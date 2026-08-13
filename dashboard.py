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


@app.route('/api/cleanup-all', methods=['POST'])
def cleanup_all():
    """Delete all leads."""
    db = SessionLocal()
    try:
        count = db.query(Lead).count()
        db.query(Lead).delete()
        db.commit()
        db.close()
        return jsonify({'success': True, 'deleted': count}), 200
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
