import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
DB_PATH = os.getenv('DB_PATH', './leads.db')
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 5000))

SEARCH_QUERIES = {
    'concrete': 'concrete contractor',
    'hardscaping': 'hardscaping contractor',
    'hardlandscaping': 'hardlandscaping contractor',
}

LOCATIONS = [
    {'city': 'Austin', 'state': 'TX'},
    {'city': 'Dallas', 'state': 'TX'},
    # Add more cities here
]

RADIUS_METERS = 15000
LANGUAGE = 'en'

REVIEW_COUNT_THRESHOLD = 10
PRIORITY_FLAGS = {
    'no_website': 'High Priority - No Website',
    'low_reviews': 'Flag - Low Review Count',
    'inactive': 'Flag - Possibly Inactive',
}
