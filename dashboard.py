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

# Initialize DB on first request
_db_initialized = False

def ensure_db_initialized():
    """Initialize DB lazily on first request, not during build phase."""
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"Warning: DB initialization deferred - {str(e)}", flush=True)

@app.before_request
def before_request():
    """Ensure DB is initialized before handling requests."""
    ensure_db_initialized()

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


@app.route('/clear-all', methods=['POST'])
def clear_all():
    """Delete all leads from database."""
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


@app.route('/admin/sync-fresh-leads', methods=['POST'])
def sync_fresh_leads():
    """Admin endpoint to replace all leads with fresh ones from local backup."""
    import json

    db = SessionLocal()

    try:
        # The 49 fresh leads to load
        fresh_leads_data = [
            {"id":"26918214-d35c-4697-865a-5e5607442e1d","name":"RJ Concrete Contractor Phoenix","phone":"(480) 573-8327","email":None,"location":None,"city":"Paradise Valley","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092017","last_updated":"2026-08-14 00:51:21.092021","follow_up_date":None},
            {"id":"29c6fb1d-cb7c-4d4e-8b95-e4ea46031143","name":"MM Concrete & Construction LLC","phone":"(602) 370-5092","email":None,"location":None,"city":"Paradise Valley","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092022","last_updated":"2026-08-14 00:51:21.092022","follow_up_date":None},
            {"id":"107b1a51-ae54-46b4-816e-a6aef96c73e0","name":"Vanguard Professional Concrete Contractors","phone":"(602) 560-5071","email":None,"location":None,"city":"Paradise Valley","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092023","last_updated":"2026-08-14 00:51:21.092024","follow_up_date":None},
            {"id":"5fb1735e-d5cb-498c-8d15-7f6b28629c16","name":"Parker Brothers Concrete LLC","phone":"(623) 248-6634","email":None,"location":None,"city":"Sun City","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092024","last_updated":"2026-08-14 00:51:21.092025","follow_up_date":None},
            {"id":"c22becd1-0576-4f11-ab93-f0a565eb72c6","name":"4C Concrete LLC","phone":"(602) 566-3813","email":None,"location":None,"city":"Avondale","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092025","last_updated":"2026-08-14 00:51:21.092026","follow_up_date":None},
            {"id":"3769017b-6ecb-41f8-b09e-3a401f1c9c2e","name":"Trademark Concrete Co.","phone":"(602) 499-6420","email":None,"location":None,"city":"Avondale","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092026","last_updated":"2026-08-14 00:51:21.092027","follow_up_date":None},
            {"id":"1c163b8b-abaf-4185-8f4a-7ba1f09f249a","name":"Caballero's Ready Mix","phone":"(480) 509-8564","email":None,"location":None,"city":"Avondale","state":"AZ","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092027","last_updated":"2026-08-14 00:51:21.092028","follow_up_date":None},
            {"id":"00cb8924-5067-4dd9-a7f5-ebe90ef08884","name":"Lady Concrete LLC","phone":"(720) 220-5511","email":None,"location":None,"city":"Lafayette","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092028","last_updated":"2026-08-14 00:51:21.092029","follow_up_date":None},
            {"id":"b3e0ba9b-8340-416f-88ac-4371412d1baf","name":"Armandos Concrete","phone":"(303) 255-1767","email":None,"location":None,"city":"Northglenn","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092029","last_updated":"2026-08-14 00:51:21.092030","follow_up_date":None},
            {"id":"8f0c7193-46a0-485c-837b-3fa9a8bfb5fa","name":"Yanez Concrete and Home Services LLC","phone":"(720) 483-8789","email":None,"location":None,"city":"Northglenn","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092031","last_updated":"2026-08-14 00:51:21.092031","follow_up_date":None},
            {"id":"b4ba6b32-a710-48f4-87c5-8e9bbecccbac","name":"FDW Concrete Inc","phone":"(303) 688-2918","email":None,"location":None,"city":"Castle Rock","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092031","last_updated":"2026-08-14 00:51:21.092032","follow_up_date":None},
            {"id":"b09196da-dcb7-4100-a208-97b5fbf53330","name":"KMR Concrete LLC","phone":"(720) 490-8921","email":None,"location":None,"city":"Westminster","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092032","last_updated":"2026-08-14 00:51:21.092033","follow_up_date":None},
            {"id":"6e30bdbe-311c-47de-8169-64ecd567c38b","name":"Meadows Concrete Construction","phone":"(303) 430-1353","email":None,"location":None,"city":"Westminster","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092033","last_updated":"2026-08-14 00:51:21.092034","follow_up_date":None},
            {"id":"d67829ba-16d7-43e1-8754-a02d009673cf","name":"Cito Concrete Contractors Inc","phone":"(303) 940-8206","email":None,"location":None,"city":"Broomfield","state":"CO","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092034","last_updated":"2026-08-14 00:51:21.092035","follow_up_date":None},
            {"id":"dd98fc14-7ffb-4de6-98b7-64a4d2022212","name":"Maya Concrete","phone":"(980) 208-3881","email":None,"location":None,"city":"Fort Mill","state":"SC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092035","last_updated":"2026-08-14 00:51:21.092036","follow_up_date":None},
            {"id":"af54fd45-6669-4a51-83b4-9825f0868c44","name":"Morgan Construction Co","phone":"(803) 328-2164","email":None,"location":None,"city":"Rock Hill","state":"SC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092036","last_updated":"2026-08-14 00:51:21.092037","follow_up_date":None},
            {"id":"bf4d1be5-d0ff-4da1-8777-e2dfb52517c8","name":"S&Z Concrete Work","phone":"(803) 448-0763","email":None,"location":None,"city":"Rock Hill","state":"SC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092037","last_updated":"2026-08-14 00:51:21.092037","follow_up_date":None},
            {"id":"7a98215f-f42f-4420-9249-71bebf0ac3bf","name":"Ron's Concrete Finishing","phone":"(704) 933-1704","email":None,"location":None,"city":"Kannapolis","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092038","last_updated":"2026-08-14 00:51:21.092038","follow_up_date":None},
            {"id":"bf0fb8fc-e37a-4f5b-afa0-6ac3b2feb258","name":"Concrete Salazar","phone":"(980) 504-2997","email":None,"location":None,"city":"Kannapolis","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092039","last_updated":"2026-08-14 00:51:21.092039","follow_up_date":None},
            {"id":"187d2d5b-e9b1-4d5a-b6d2-143f4903c719","name":"Ashworth Concrete & Grading","phone":"(704) 507-6116","email":None,"location":None,"city":"Kannapolis","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092040","last_updated":"2026-08-14 00:51:21.092040","follow_up_date":None},
            {"id":"968e9504-bde3-4db7-a9d3-5edfd10491e8","name":"MDG Concrete Services LLP","phone":"(980) 622-6590","email":None,"location":None,"city":"China Grove","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092041","last_updated":"2026-08-14 00:51:21.092041","follow_up_date":None},
            {"id":"8c5c1f76-694b-46bb-b008-1cfd5024cb1e","name":"Cabarrus Concrete","phone":"(704) 216-3102","email":None,"location":None,"city":"Salisbury","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092042","last_updated":"2026-08-14 00:51:21.092043","follow_up_date":None},
            {"id":"c11e872e-f125-4715-a2c6-6561448c593c","name":"Jmy Building Group LLC","phone":"(704) 963-3223","email":None,"location":None,"city":"Salisbury","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092043","last_updated":"2026-08-14 00:51:21.092044","follow_up_date":None},
            {"id":"e4977254-f2e8-4e01-b84f-9fc7d14ee18b","name":"P C Masonry & Concrete","phone":"(704) 857-4515","email":None,"location":None,"city":"Salisbury","state":"NC","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092044","last_updated":"2026-08-14 00:51:21.092045","follow_up_date":None},
            {"id":"81de9f53-28ef-44ba-843e-3b0dffdb4cf8","name":"Elite Concrete Clarksville","phone":"(931) 251-9471","email":None,"location":None,"city":"Clarksville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092045","last_updated":"2026-08-14 00:51:21.092045","follow_up_date":None},
            {"id":"1c134670-658c-4360-ad47-870da08e637e","name":"TCB Concrete","phone":"(931) 378-2649","email":None,"location":None,"city":"Clarksville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092046","last_updated":"2026-08-14 00:51:21.092046","follow_up_date":None},
            {"id":"f426c703-953b-49b9-a2ab-e989c87814f9","name":"Martinez Concrete","phone":"(931) 237-9908","email":None,"location":None,"city":"Clarksville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092047","last_updated":"2026-08-14 00:51:21.092047","follow_up_date":None},
            {"id":"6b3d2d94-e099-4a13-b0e8-b928773e0c49","name":"Top Choice Concrete","phone":"(931) 302-2509","email":None,"location":None,"city":"Clarksville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092048","last_updated":"2026-08-14 00:51:21.092048","follow_up_date":None},
            {"id":"02b848eb-7dae-414f-bb03-2c933bd4b447","name":"Hazlett's Concrete","phone":"(931) 216-2788","email":None,"location":None,"city":"Clarksville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092049","last_updated":"2026-08-14 00:51:21.092049","follow_up_date":None},
            {"id":"f31cfe33-6bc6-4cbe-89f4-ce3e76b993cf","name":"Arnold Concrete Inc.","phone":"(615) 790-2639","email":None,"location":None,"city":"Franklin","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092050","last_updated":"2026-08-14 00:51:21.092050","follow_up_date":None},
            {"id":"738eb77d-7829-489a-9ae7-7e067e0387fb","name":"Zane Davis Concrete","phone":"(615) 948-5543","email":None,"location":None,"city":"Franklin","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092051","last_updated":"2026-08-14 00:51:21.092051","follow_up_date":None},
            {"id":"3f8bc055-ceb5-4b66-843b-80eed996c784","name":"Nashville Concrete Contractor","phone":"(615) 704-2240","email":None,"location":None,"city":"Brentwood","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092052","last_updated":"2026-08-14 00:51:21.092052","follow_up_date":None},
            {"id":"39a0eb55-fa26-4795-ab73-8cec9cb2a178","name":"Concrete Pros Of Nashville","phone":"(615) 239-1809","email":None,"location":None,"city":"Brentwood","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092053","last_updated":"2026-08-14 00:51:21.092053","follow_up_date":None},
            {"id":"0cbd40d6-b29c-494b-be5f-b10e62ceed2b","name":"Midstate Mobile Concrete","phone":"(615) 533-2315","email":None,"location":None,"city":"Mount Juliet","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092054","last_updated":"2026-08-14 00:51:21.092054","follow_up_date":None},
            {"id":"a68d3a48-60a2-4bc7-ad90-926c539af5a9","name":"Blue Ribbon Concrete Services","phone":"(615) 642-1020","email":None,"location":None,"city":"Mount Juliet","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092055","last_updated":"2026-08-14 00:51:21.092055","follow_up_date":None},
            {"id":"50c8a13a-a453-4864-8811-d5ffe6d5e89d","name":"Backyard Builders","phone":"(615) 579-4556","email":None,"location":None,"city":"Hendersonville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092056","last_updated":"2026-08-14 00:51:21.092056","follow_up_date":None},
            {"id":"cbe9399b-14b0-41c4-a7c9-d6fb298b75bc","name":"Southeastern Concrete","phone":"(615) 347-1419","email":None,"location":None,"city":"Hendersonville","state":"TN","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092057","last_updated":"2026-08-14 00:51:21.092057","follow_up_date":None},
            {"id":"ca7602c5-64c8-41a0-9883-26a06949357a","name":"GSA Concrete","phone":"(760) 334-3536","email":None,"location":None,"city":"Carlsbad","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092057","last_updated":"2026-08-14 00:51:21.092058","follow_up_date":None},
            {"id":"652d2737-a2c4-441c-9938-5c73c57c2345","name":"Klaus Enyedi Concrete","phone":"(760) 931-0445","email":None,"location":None,"city":"Carlsbad","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092058","last_updated":"2026-08-14 00:51:21.092059","follow_up_date":None},
            {"id":"d64a2f98-1452-4371-be63-53094b733d64","name":"Blaise Concrete Cutting","phone":"(760) 815-0361","email":None,"location":None,"city":"Encinitas","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092059","last_updated":"2026-08-14 00:51:21.092060","follow_up_date":None},
            {"id":"84f532c9-abcd-4454-87ed-d5d649291212","name":"Oceanside Concrete Services","phone":"(760) 492-6717","email":None,"location":None,"city":"Oceanside","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092060","last_updated":"2026-08-14 00:51:21.092061","follow_up_date":None},
            {"id":"972ecf7d-cfc5-4739-bf6e-cfb846d97d21","name":"Terry's Concrete","phone":"(760) 519-2504","email":None,"location":None,"city":"Oceanside","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092061","last_updated":"2026-08-14 00:51:21.092062","follow_up_date":None},
            {"id":"d6aceb6b-67c5-430f-8578-4bf8d38cb2ea","name":"Lunada Bay Concrete Inc","phone":"(760) 231-9018","email":None,"location":None,"city":"Oceanside","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092062","last_updated":"2026-08-14 00:51:21.092062","follow_up_date":None},
            {"id":"a0d75aaf-e0b7-41d2-a180-f5f4a9bb9bac","name":"Blue Coast Concrete Inc.","phone":"(760) 908-3069","email":None,"location":None,"city":"Oceanside","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092063","last_updated":"2026-08-14 00:51:21.092063","follow_up_date":None},
            {"id":"0968bf02-aa85-4fea-9104-0a781c931283","name":"Elite Concrete, Inc.","phone":"(760) 691-1993","email":None,"location":None,"city":"Escondido","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092064","last_updated":"2026-08-14 00:51:21.092064","follow_up_date":None},
            {"id":"e2ad2074-fcf2-44a8-ab88-d7c939d753ea","name":"Integrity Concrete","phone":"(760) 233-0044","email":None,"location":None,"city":"Escondido","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092065","last_updated":"2026-08-14 00:51:21.092065","follow_up_date":None},
            {"id":"d682834d-0de9-41bc-baf4-4d45027970c4","name":"Betz Concrete Inc","phone":"(760) 737-0444","email":None,"location":None,"city":"Escondido","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092066","last_updated":"2026-08-14 00:51:21.092066","follow_up_date":None},
            {"id":"6d237642-7a28-415a-87fd-3806747e98f7","name":"E&A Concrete Evolution, Inc.","phone":"(760) 522-7723","email":None,"location":None,"city":"Escondido","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092067","last_updated":"2026-08-14 00:51:21.092067","follow_up_date":None},
            {"id":"8fb3bace-eff2-439b-844e-928a8c960259","name":"Carson's Custom Concrete","phone":"(760) 735-9042","email":None,"location":None,"city":"Escondido","state":"CA","qualification":"good","setter_notes":None,"call_status":"not_contacted","call_outcome":None,"attempts":0,"last_contact_attempt":None,"website":None,"rating":None,"review_count":0,"address":None,"category":None,"no_website":0,"low_reviews":0,"possibly_inactive":0,"priority_score":0.0,"added_date":"2026-08-14 00:51:21.092068","last_updated":"2026-08-14 00:51:21.092068","follow_up_date":None},
        ]

        # Step 1: Delete all existing leads
        print(f"🗑️  Deleting old leads...", flush=True)
        old_count = db.query(Lead).count()
        db.query(Lead).delete()
        db.commit()
        print(f"✅ Deleted {old_count} old leads", flush=True)

        # Step 2: Insert fresh leads
        print(f"📥 Inserting 49 fresh leads...", flush=True)
        for lead_data in fresh_leads_data:
            lead = Lead(
                id=lead_data['id'],
                name=lead_data['name'],
                phone=lead_data['phone'],
                email=lead_data['email'],
                location=lead_data['location'],
                city=lead_data['city'],
                state=lead_data['state'],
                qualification=lead_data['qualification'],
                setter_notes=lead_data['setter_notes'],
                call_status=lead_data['call_status'],
                call_outcome=lead_data['call_outcome'],
                attempts=lead_data['attempts'],
                last_contact_attempt=lead_data['last_contact_attempt'],
                website=lead_data['website'],
                rating=lead_data['rating'],
                review_count=lead_data['review_count'],
                address=lead_data['address'],
                category=lead_data['category'],
                no_website=bool(lead_data['no_website']),
                low_reviews=bool(lead_data['low_reviews']),
                possibly_inactive=bool(lead_data['possibly_inactive']),
                priority_score=lead_data['priority_score'],
            )
            db.add(lead)

        db.commit()
        print(f"✅ Inserted {len(fresh_leads_data)} fresh leads", flush=True)

        # Step 3: Verify
        final_count = db.query(Lead).count()
        print(f"✨ Final count: {final_count} leads in database", flush=True)

        db.close()
        return jsonify({
            'success': True,
            'deleted': old_count,
            'inserted': len(fresh_leads_data),
            'final_count': final_count,
            'message': f'✅ Successfully replaced {old_count} old leads with {len(fresh_leads_data)} fresh leads!'
        }), 200

    except Exception as e:
        db.close()
        print(f"❌ Error: {str(e)}", flush=True)
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=True)
