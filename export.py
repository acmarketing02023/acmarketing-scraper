import csv
from datetime import datetime
from database import SessionLocal, Lead


def export_leads_to_csv(filters=None, output_path=None):
    """
    Export leads to CSV file.

    Args:
        filters: dict with optional keys: city, category, has_website (bool), priority_only (bool)
        output_path: custom output path, defaults to leads_export_TIMESTAMP.csv

    Returns:
        Path to exported CSV file
    """
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'leads_export_{timestamp}.csv'

    db = SessionLocal()
    query = db.query(Lead)

    # Apply filters
    if filters:
        if filters.get('city'):
            query = query.filter(Lead.city == filters['city'])
        if filters.get('category'):
            query = query.filter(Lead.category == filters['category'])
        if filters.get('has_website') is not None:
            if filters['has_website']:
                query = query.filter(Lead.website.isnot(None))
            else:
                query = query.filter(Lead.website.is_(None))
        if filters.get('priority_only'):
            query = query.filter(
                (Lead.no_website == True) |
                (Lead.low_reviews == True) |
                (Lead.possibly_inactive == True)
            )

    # Sort by priority score (highest first)
    leads = query.order_by(Lead.priority_score.desc()).all()

    # Write to CSV
    fieldnames = [
        'Business Name',
        'Phone',
        'Website',
        'Rating',
        'Review Count',
        'Address',
        'City',
        'State',
        'Category',
        'No Website',
        'Low Reviews',
        'Possibly Inactive',
        'Priority Score',
        'First Seen',
        'Last Updated',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            writer.writerow({
                'Business Name': lead.name,
                'Phone': lead.phone or '',
                'Website': lead.website or '',
                'Rating': lead.rating or '',
                'Review Count': lead.review_count or 0,
                'Address': lead.address or '',
                'City': lead.city or '',
                'State': lead.state or '',
                'Category': lead.category or '',
                'No Website': 'Yes' if lead.no_website else 'No',
                'Low Reviews': 'Yes' if lead.low_reviews else 'No',
                'Possibly Inactive': 'Yes' if lead.possibly_inactive else 'No',
                'Priority Score': lead.priority_score,
                'First Seen': lead.first_seen.strftime('%Y-%m-%d %H:%M:%S'),
                'Last Updated': lead.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
            })

    db.close()
    print(f'✓ Exported {len(leads)} leads to {output_path}')
    return output_path


if __name__ == '__main__':
    export_leads_to_csv()
