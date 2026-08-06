import googlemaps
import time
from datetime import datetime
from sqlalchemy.orm import Session
from database import Lead, SessionLocal
from scoring import score_lead, apply_scoring_to_lead
from config import (
    GOOGLE_PLACES_API_KEY,
    SEARCH_QUERIES,
    LOCATIONS,
    RADIUS_METERS,
    LANGUAGE,
)


def get_location_coordinates(city, state):
    """
    Get latitude/longitude for a city, state.
    Uses a simple geocoding approach via Google Places API.
    """
    gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)
    try:
        geocode_result = gmaps.geocode(f'{city}, {state}')
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        print(f'Error geocoding {city}, {state}: {e}')
    return None, None


def search_businesses(query, lat, lng, radius=RADIUS_METERS):
    """
    Search for businesses using Google Places API.
    Returns a list of place results.
    """
    gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)
    results = []
    next_page_token = None

    try:
        while True:
            places = gmaps.places_nearby(
                location=(lat, lng),
                radius=radius,
                keyword=query,
                language=LANGUAGE,
                page_token=next_page_token,
            )

            results.extend(places.get('results', []))
            next_page_token = places.get('next_page_token')

            if not next_page_token:
                break

            time.sleep(2)  # Respect API rate limits

    except Exception as e:
        print(f'Error searching for {query} near {lat},{lng}: {e}')

    return results


def extract_place_details(place, category):
    """
    Extract relevant details from a Google Places result.
    """
    return {
        'id': place.get('place_id'),
        'name': place.get('name'),
        'rating': place.get('rating'),
        'review_count': place.get('user_ratings_total', 0),
        'address': place.get('vicinity', ''),
        'category': category,
        'phone': None,
        'website': None,
        'lat': place.get('geometry', {}).get('location', {}).get('lat'),
        'lng': place.get('geometry', {}).get('location', {}).get('lng'),
    }


def get_place_full_details(place_id):
    """
    Get full place details including phone and website.
    """
    gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)
    try:
        place_details = gmaps.place(
            place_id=place_id,
            fields=['formatted_phone_number', 'website', 'address_components'],
        )
        result = place_details.get('result', {})
        return {
            'phone': result.get('formatted_phone_number'),
            'website': result.get('website'),
            'address_components': result.get('address_components', []),
        }
    except Exception as e:
        print(f'Error fetching details for {place_id}: {e}')
        return {}


def parse_city_from_address_components(components):
    """Extract city from address components."""
    for component in components:
        if 'locality' in component.get('types', []):
            return component.get('long_name')
    return None


def upsert_lead(db: Session, lead_data):
    """
    Insert or update a lead in the database.
    Returns True if new, False if updated.
    """
    existing_lead = db.query(Lead).filter(Lead.id == lead_data['id']).first()

    scoring_result = score_lead(lead_data)

    if existing_lead:
        existing_lead.phone = lead_data.get('phone') or existing_lead.phone
        existing_lead.website = lead_data.get('website') or existing_lead.website
        existing_lead.rating = lead_data.get('rating') or existing_lead.rating
        existing_lead.review_count = lead_data.get('review_count', 0)
        existing_lead.last_updated = datetime.utcnow()
        existing_lead.last_checked = datetime.utcnow()
        apply_scoring_to_lead(existing_lead, scoring_result)
        db.commit()
        return False
    else:
        new_lead = Lead(
            id=lead_data['id'],
            name=lead_data['name'],
            phone=lead_data.get('phone'),
            website=lead_data.get('website'),
            rating=lead_data.get('rating'),
            review_count=lead_data.get('review_count', 0),
            address=lead_data.get('address'),
            city=lead_data.get('city'),
            state=lead_data.get('state'),
            category=lead_data['category'],
        )
        apply_scoring_to_lead(new_lead, scoring_result)
        db.add(new_lead)
        db.commit()
        return True


def scrape_all_locations():
    """
    Main scraping function. Searches all configured locations and queries.
    """
    db = SessionLocal()
    total_new = 0
    total_updated = 0

    try:
        for location in LOCATIONS:
            city = location['city']
            state = location['state']

            lat, lng = get_location_coordinates(city, state)
            if not lat or not lng:
                print(f'Could not geocode {city}, {state}')
                continue

            print(f'\nSearching {city}, {state} ({lat}, {lng})...')

            for category_key, query in SEARCH_QUERIES.items():
                print(f'  Searching for: {query}')
                places = search_businesses(query, lat, lng)

                for place in places:
                    # Extract basic details
                    lead_data = extract_place_details(place, category_key)

                    # Get full details (phone, website)
                    full_details = get_place_full_details(lead_data['id'])
                    lead_data['phone'] = full_details.get('phone')
                    lead_data['website'] = full_details.get('website')

                    # Parse city from address components
                    city_parsed = parse_city_from_address_components(
                        full_details.get('address_components', [])
                    )
                    if city_parsed:
                        lead_data['city'] = city_parsed
                    else:
                        lead_data['city'] = city

                    lead_data['state'] = state

                    # Upsert to database
                    is_new = upsert_lead(db, lead_data)
                    if is_new:
                        total_new += 1
                    else:
                        total_updated += 1

                    time.sleep(0.5)  # Rate limiting

    finally:
        db.close()

    print(f'\n✓ Scraping complete: {total_new} new leads, {total_updated} updated.')
    return total_new, total_updated


if __name__ == '__main__':
    from database import init_db
    init_db()
    scrape_all_locations()
