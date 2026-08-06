from database import SessionLocal, Lead, init_db
from datetime import datetime

init_db()
db = SessionLocal()

sample_leads = [
    {
        'id': 'place_001',
        'name': 'Austin Concrete Solutions',
        'phone': '(512) 555-0101',
        'website': 'https://austinconcrete.com',
        'rating': 4.8,
        'review_count': 47,
        'address': '1234 Main St, Austin, TX 78701',
        'city': 'Austin',
        'state': 'TX',
        'category': 'concrete',
        'no_website': False,
        'low_reviews': False,
        'possibly_inactive': False,
        'priority_score': 0.0,
    },
    {
        'id': 'place_002',
        'name': 'Dallas Hardscaping Pro',
        'phone': '(214) 555-0202',
        'website': None,
        'rating': 4.2,
        'review_count': 12,
        'address': '5678 Commerce Dr, Dallas, TX 75201',
        'city': 'Dallas',
        'state': 'TX',
        'category': 'hardscaping',
        'no_website': True,
        'low_reviews': False,
        'possibly_inactive': False,
        'priority_score': 100.0,
    },
    {
        'id': 'place_003',
        'name': 'Premium Concrete Services',
        'phone': None,
        'website': None,
        'rating': 3.9,
        'review_count': 3,
        'address': '2345 Oak Ave, Austin, TX 78704',
        'city': 'Austin',
        'state': 'TX',
        'category': 'concrete',
        'no_website': True,
        'low_reviews': True,
        'possibly_inactive': False,
        'priority_score': 150.0,
    },
    {
        'id': 'place_004',
        'name': 'Landscape & Hardscape Design',
        'phone': '(512) 555-0404',
        'website': 'https://landscapedesign.com',
        'rating': 4.6,
        'review_count': 28,
        'address': '3456 Park Blvd, Austin, TX 78702',
        'city': 'Austin',
        'state': 'TX',
        'category': 'hardlandscaping',
        'no_website': False,
        'low_reviews': False,
        'possibly_inactive': False,
        'priority_score': 0.0,
    },
    {
        'id': 'place_005',
        'name': 'North Star Concrete',
        'phone': '(214) 555-0505',
        'website': None,
        'rating': None,
        'review_count': 0,
        'address': '7890 Industrial Pkwy, Dallas, TX 75207',
        'city': 'Dallas',
        'state': 'TX',
        'category': 'concrete',
        'no_website': True,
        'low_reviews': False,
        'possibly_inactive': True,
        'priority_score': 130.0,
    },
    {
        'id': 'place_006',
        'name': 'Elite Hardscaping Solutions',
        'phone': '(512) 555-0606',
        'website': None,
        'rating': 4.1,
        'review_count': 8,
        'address': '4567 Tech Ridge, Austin, TX 78741',
        'city': 'Austin',
        'state': 'TX',
        'category': 'hardscaping',
        'no_website': True,
        'low_reviews': True,
        'possibly_inactive': False,
        'priority_score': 125.0,
    },
    {
        'id': 'place_007',
        'name': 'Texas Concrete Experts',
        'phone': '(469) 555-0707',
        'website': 'https://texasconcrete.net',
        'rating': 4.4,
        'review_count': 34,
        'address': '6789 Highway 75, Dallas, TX 75211',
        'city': 'Dallas',
        'state': 'TX',
        'category': 'concrete',
        'no_website': False,
        'low_reviews': False,
        'possibly_inactive': False,
        'priority_score': 0.0,
    },
    {
        'id': 'place_008',
        'name': 'Quality Landscape & Hardscape',
        'phone': None,
        'website': None,
        'rating': 3.7,
        'review_count': 5,
        'address': '1111 Elm St, Austin, TX 78703',
        'city': 'Austin',
        'state': 'TX',
        'category': 'hardlandscaping',
        'no_website': True,
        'low_reviews': True,
        'possibly_inactive': False,
        'priority_score': 125.0,
    },
]

for lead_data in sample_leads:
    existing = db.query(Lead).filter(Lead.id == lead_data['id']).first()
    if not existing:
        lead = Lead(**lead_data)
        lead.first_seen = datetime.utcnow()
        lead.last_updated = datetime.utcnow()
        db.add(lead)

db.commit()
db.close()

print(f'✓ Added {len(sample_leads)} sample leads')
