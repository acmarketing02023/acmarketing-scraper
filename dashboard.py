from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from database import SessionLocal, Lead, init_db
from config import DASHBOARD_HOST, DASHBOARD_PORT
from datetime import datetime
import uuid
import os
import csv
import requests
from io import StringIO

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize DB on startup
init_db()

# One-time: Replace all leads with the 49 new ones if we have 80 or more
db_check = SessionLocal()
current_count = db_check.query(Lead).count()
if current_count >= 80:
    print("🔄 Replacing leads with fresh 49...", flush=True)
    # Delete all existing leads
    db_check.query(Lead).delete()
    db_check.commit()

    # Add the 49 new leads
    import uuid
    new_leads_data = [
        ("RJ Concrete Contractor Phoenix", "(480) 573-8327", "Paradise Valley", "AZ"),
        ("MM Concrete & Construction LLC", "(602) 370-5092", "Paradise Valley", "AZ"),
        ("Vanguard Professional Concrete Contractors", "(602) 560-5071", "Paradise Valley", "AZ"),
        ("Parker Brothers Concrete LLC", "(623) 248-6634", "Sun City", "AZ"),
        ("4C Concrete LLC", "(602) 566-3813", "Avondale", "AZ"),
        ("Trademark Concrete Co.", "(602) 499-6420", "Avondale", "AZ"),
        ("Caballero's Ready Mix", "(480) 509-8564", "Avondale", "AZ"),
        ("Lady Concrete LLC", "(720) 220-5511", "Lafayette", "CO"),
        ("Armandos Concrete", "(303) 255-1767", "Northglenn", "CO"),
        ("Yanez Concrete and Home Services LLC", "(720) 483-8789", "Northglenn", "CO"),
        ("FDW Concrete Inc", "(303) 688-2918", "Castle Rock", "CO"),
        ("KMR Concrete LLC", "(720) 490-8921", "Westminster", "CO"),
        ("Meadows Concrete Construction", "(303) 430-1353", "Westminster", "CO"),
        ("Cito Concrete Contractors Inc", "(303) 940-8206", "Broomfield", "CO"),
        ("Maya Concrete", "(980) 208-3881", "Fort Mill", "SC"),
        ("Morgan Construction Co", "(803) 328-2164", "Rock Hill", "SC"),
        ("S&Z Concrete Work", "(803) 448-0763", "Rock Hill", "SC"),
        ("Ron's Concrete Finishing", "(704) 933-1704", "Kannapolis", "NC"),
        ("Concrete Salazar", "(980) 504-2997", "Kannapolis", "NC"),
        ("Ashworth Concrete & Grading", "(704) 507-6116", "Kannapolis", "NC"),
        ("MDG Concrete Services LLP", "(980) 622-6590", "China Grove", "NC"),
        ("Cabarrus Concrete", "(704) 216-3102", "Salisbury", "NC"),
        ("Jmy Building Group LLC", "(704) 963-3223", "Salisbury", "NC"),
        ("P C Masonry & Concrete", "(704) 857-4515", "Salisbury", "NC"),
        ("Elite Concrete Clarksville", "(931) 251-9471", "Clarksville", "TN"),
        ("TCB Concrete", "(931) 378-2649", "Clarksville", "TN"),
        ("Martinez Concrete", "(931) 237-9908", "Clarksville", "TN"),
        ("Top Choice Concrete", "(931) 302-2509", "Clarksville", "TN"),
        ("Hazlett's Concrete", "(931) 216-2788", "Clarksville", "TN"),
        ("Arnold Concrete Inc.", "(615) 790-2639", "Franklin", "TN"),
        ("Zane Davis Concrete", "(615) 948-5543", "Franklin", "TN"),
        ("Nashville Concrete Contractor", "(615) 704-2240", "Brentwood", "TN"),
        ("Concrete Pros Of Nashville", "(615) 239-1809", "Brentwood", "TN"),
        ("Midstate Mobile Concrete", "(615) 533-2315", "Mount Juliet", "TN"),
        ("Blue Ribbon Concrete Services", "(615) 642-1020", "Mount Juliet", "TN"),
        ("Backyard Builders", "(615) 579-4556", "Hendersonville", "TN"),
        ("Southeastern Concrete", "(615) 347-1419", "Hendersonville", "TN"),
        ("GSA Concrete", "(760) 334-3536", "Carlsbad", "CA"),
        ("Klaus Enyedi Concrete", "(760) 931-0445", "Carlsbad", "CA"),
        ("Blaise Concrete Cutting", "(760) 815-0361", "Encinitas", "CA"),
        ("Oceanside Concrete Services", "(760) 492-6717", "Oceanside", "CA"),
        ("Terry's Concrete", "(760) 519-2504", "Oceanside", "CA"),
        ("Lunada Bay Concrete Inc", "(760) 231-9018", "Oceanside", "CA"),
        ("Blue Coast Concrete Inc.", "(760) 908-3069", "Oceanside", "CA"),
        ("Elite Concrete, Inc.", "(760) 691-1993", "Escondido", "CA"),
        ("Integrity Concrete", "(760) 233-0044", "Escondido", "CA"),
        ("Betz Concrete Inc", "(760) 737-0444", "Escondido", "CA"),
        ("E&A Concrete Evolution, Inc.", "(760) 522-7723", "Escondido", "CA"),
        ("Carson's Custom Concrete", "(760) 735-9042", "Escondido", "CA"),
    ]

    for name, phone, city, state in new_leads_data:
        lead = Lead(
            id=str(uuid.uuid4()),
            name=name,
            phone=phone,
            city=city,
            state=state,
            qualification='good',
            call_status='not_contacted'
        )
        db_check.add(lead)

    db_check.commit()
    print(f"✅ Database reset to 49 fresh leads", flush=True)

db_check.close()

# Setter CRM Configuration
SETTER_CRM_API = "https://setter-crm-kappa.vercel.app/api/calls"


def sync_to_setter_crm(lead):
    """Send call log to Setter CRM."""
    try:
        # Map call_status to CRM outcome format
        outcome_map = {
            'attempted': 'NO_ANSWER',
            'connected': 'NOT_INTERESTED',
        }

        outcome = outcome_map.get(lead.call_status, 'NO_ANSWER')

        payload = {
            'contractorName': lead.name,
            'phone': lead.phone,
            'outcome': outcome,
        }

        # Add API key for authentication
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': 'sk-scraper-acmarketing-9f8d7e6c5b4a3z2x',
        }

        response = requests.post(SETTER_CRM_API, json=payload, headers=headers, timeout=5)

        if response.status_code in [200, 201]:
            print(f"✅ Synced to Setter CRM: {lead.name}", flush=True)
            return True
        else:
            print(f"⚠️ Setter CRM sync failed: {response.status_code}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Error syncing to Setter CRM: {str(e)}", flush=True)
        return False


@app.route('/api/leads/<lead_id>/delete', methods=['POST'])
def delete_lead(lead_id):
    """Delete a specific lead."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            db.delete(lead)
            db.commit()
        db.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/')
def index():
    """Dashboard homepage."""
    return render_template('index.html')


@app.route('/add-lead')
def add_lead_page():
    """Page to add a new lead."""
    return render_template('add_lead.html')


@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Fetch leads with filters and sorting."""
    db = SessionLocal()

    # Get filter parameters
    city = request.args.get('city', '')
    qualification = request.args.get('qualification', '')
    call_status = request.args.get('call_status', '')
    sort_by = request.args.get('sort_by', 'priority_score')
    sort_order = request.args.get('sort_order', 'desc')

    query = db.query(Lead)

    # Apply filters
    if city and city != 'all':
        query = query.filter(Lead.city == city)
    if qualification and qualification != 'all':
        query = query.filter(Lead.qualification == qualification)
    if call_status:
        query = query.filter(Lead.call_status == call_status)

    # Sorting
    if sort_order == 'desc':
        query = query.order_by(getattr(Lead, sort_by).desc())
    else:
        query = query.order_by(getattr(Lead, sort_by).asc())

    # Get counts for all statuses
    all_leads = db.query(Lead).all()
    all_counts = {
        'all': len(all_leads),
        'not_contacted': len([l for l in all_leads if l.call_status == 'not_contacted']),
        'attempted': len([l for l in all_leads if l.call_status == 'attempted']),
        'connected': len([l for l in all_leads if l.call_status == 'connected']),
        'scheduled': len([l for l in all_leads if l.call_status == 'scheduled']),
    }

    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 50
    total = query.count()
    leads = query.offset((page - 1) * per_page).limit(per_page).all()

    lead_list = [
        {
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'email': lead.email,
            'location': lead.location,
            'city': lead.city,
            'state': lead.state,
            'qualification': lead.qualification,
            'call_status': lead.call_status,
            'attempts': lead.attempts,
            'setter_notes': lead.setter_notes,
            'priority_score': lead.priority_score,
            'last_updated': lead.last_updated.isoformat(),
        }
        for lead in leads
    ]

    db.close()

    return jsonify({
        'leads': lead_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'all_counts': all_counts,
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics."""
    db = SessionLocal()

    total_leads = db.query(Lead).count()
    leads_with_website = db.query(Lead).filter(Lead.website.isnot(None)).count()
    high_priority = db.query(Lead).filter(
        (Lead.no_website == True) | (Lead.low_reviews == True)
    ).count()

    cities = db.query(Lead.city).distinct().count()
    categories = db.query(Lead.category).distinct().count()

    db.close()

    return jsonify({
        'total_leads': total_leads,
        'leads_with_website': leads_with_website,
        'leads_without_website': total_leads - leads_with_website,
        'high_priority_leads': high_priority,
        'unique_cities': cities,
        'unique_categories': categories,
    })


@app.route('/api/filters', methods=['GET'])
def get_filter_options():
    """Get available filter options."""
    db = SessionLocal()

    cities = [row[0] for row in db.query(Lead.city).distinct().all() if row[0]]
    qualifications = ['good', 'medium', 'low', 'unqualified']

    db.close()

    return jsonify({
        'cities': sorted(cities),
        'qualifications': qualifications,
    })


@app.route('/api/leads/add', methods=['POST'])
def add_lead():
    """Add a new lead manually."""
    db = SessionLocal()
    data = request.json

    try:
        # Generate unique ID
        lead_id = str(uuid.uuid4())

        new_lead = Lead(
            id=lead_id,
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            location=data.get('location'),
            city=data.get('city'),
            state=data.get('state'),
            qualification=data.get('qualification', 'unqualified'),
            setter_notes=data.get('setter_notes'),
            call_status='not_contacted',
        )

        db.add(new_lead)
        db.commit()
        db.close()

        return jsonify({'success': True, 'id': lead_id}), 201
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/leads/<lead_id>/update', methods=['POST'])
def update_lead(lead_id):
    """Update lead call status and notes, then sync to Setter CRM."""
    db = SessionLocal()
    data = request.json

    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return jsonify({'success': False, 'error': 'Lead not found'}), 404

        # Check if call_status is being updated
        is_call_logged = 'call_status' in data

        if 'call_status' in data:
            lead.call_status = data['call_status']
        if 'call_outcome' in data:
            lead.call_outcome = data['call_outcome']
        if 'attempts' in data:
            lead.attempts = data['attempts']
        if 'last_contact_attempt' in data:
            lead.last_contact_attempt = datetime.utcnow()
        if 'follow_up_date' in data:
            lead.follow_up_date = data['follow_up_date']

        lead.last_updated = datetime.utcnow()
        db.commit()

        # Sync to Setter CRM if call_status was updated (but not for 'scheduled')
        if is_call_logged and lead.call_status in ['attempted', 'connected']:
            sync_to_setter_crm(lead)

        db.close()

        return jsonify({'success': True}), 200
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/setter-script')
def setter_script():
    """Page with script and talking points for setters."""
    return render_template('setter_script.html')


if __name__ == '__main__':
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=True)
