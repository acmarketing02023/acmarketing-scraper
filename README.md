# ACMARKETING Lead Scraper

A Python-based lead generation scraper for concrete contractors and hardscaping businesses using the Google Places API.

## Features

- **Google Places API Integration**: Searches for concrete and hardscaping contractors by location
- **Smart Lead Scoring**: Flags high-priority leads (no website, low reviews, possibly inactive)
- **SQLite Database**: Stores leads without duplicates, supports repeat runs
- **CSV Export**: Generates clean CSV exports for CRM import
- **Web Dashboard**: Local web UI to view and filter leads
- **CLI Tool**: Command-line interface for scraping, exporting, and initialization

## Project Structure

```
acmarketing_scraper/
├── config.py              # Configuration and settings
├── database.py            # Database models and initialization
├── scoring.py             # Lead scoring logic
├── scraper.py             # Google Places API integration
├── export.py              # CSV export functionality
├── cli.py                 # Command-line interface
├── dashboard.py           # Flask dashboard
├── templates/             # HTML templates
│   └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
cd ~/acmarketing_scraper
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Google Places API key:

```
GOOGLE_PLACES_API_KEY=your_api_key_here
DB_PATH=./leads.db
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=5000
```

### 3. Configure Search Locations

Edit `config.py` and update the `LOCATIONS` list with your target cities:

```python
LOCATIONS = [
    {'city': 'Austin', 'state': 'TX'},
    {'city': 'Dallas', 'state': 'TX'},
    # Add more locations
]
```

### 4. Initialize Database

```bash
python cli.py init
```

## Usage

### Run Scraper

```bash
python cli.py scrape
```

This will:
- Search for concrete and hardscaping contractors in configured locations
- Store results in SQLite database (prevents duplicates)
- Score each lead based on website presence, review count, etc.

### Export to CSV

```bash
# Export all leads
python cli.py export

# Export with filters
python cli.py export --city "Austin" --category "concrete"
python cli.py export --priority-only
python cli.py export --no-website-only

# Custom output path
python cli.py export --output custom_leads.csv
```

### View Dashboard

```bash
python dashboard.py
```

Then open http://localhost:5000 in your browser.

Dashboard features:
- View all leads in a sortable table
- Filter by city, category, and website presence
- Sort by priority score, rating, review count, or name
- View statistics (total leads, high-priority, website coverage)
- Responsive design for mobile/tablet

## Scheduling (Cron)

To run the scraper automatically each night:

```bash
# Edit your crontab
crontab -e

# Add this line to run at 2 AM daily
0 2 * * * cd ~/acmarketing_scraper && python cli.py scrape && python cli.py export --output leads_`date +\%Y\%m\%d`.csv
```

## API Keys

### Getting a Google Places API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Places API
4. Create credentials (API key)
5. Add to `.env` file

**Note**: The Places API has usage quotas and costs. Check Google's pricing to understand your usage.

## Lead Scoring

Leads are scored based on:

- **No Website** (+100): High-priority flag, likely needs marketing services
- **Low Review Count** (+50): Under 10 reviews, possibly not actively marketing
- **No Reviews** (+30): Possibly inactive or brand new
- **Combined Flags** (+25): Bonus if has both no website AND low reviews

Priority score determines sort order in dashboard and exports.

## Database Schema

### Leads Table

| Field | Type | Index | Description |
|-------|------|-------|-------------|
| id | String | Yes | Google Places Place ID (primary key) |
| name | String | Yes | Business name |
| phone | String | | Phone number |
| website | String | | Website URL |
| rating | Float | | Star rating |
| review_count | Integer | | Number of reviews |
| address | String | | Full address |
| city | String | Yes | City name |
| state | String | | State |
| category | String | Yes | concrete/hardscaping |
| no_website | Boolean | Yes | Flag: has no website |
| low_reviews | Boolean | Yes | Flag: low review count |
| possibly_inactive | Boolean | Yes | Flag: possibly inactive |
| priority_score | Float | | Calculated priority score |
| first_seen | DateTime | | When lead was first scraped |
| last_updated | DateTime | | When lead data was last updated |
| last_checked | DateTime | | When lead was last checked |

## Troubleshooting

### "API key not configured"

Make sure you have `GOOGLE_PLACES_API_KEY` in your `.env` file.

### "No results found"

- Check that locations in `config.py` are spelled correctly
- Verify Google Places API is enabled in Cloud Console
- Check API quota usage in Cloud Console

### Duplicate entries after re-running scraper

The scraper uses Google Places Place IDs to prevent duplicates. If duplicates appear, they likely have different reviews/info (the upsert logic updates existing records).

## Future Enhancements

- Direct CRM API integration (Salesforce, HubSpot, Pipedrive)
- Business website quality scoring
- Contact person/email extraction
- Lead status tracking
- A/B testing support
- Automated outreach campaign triggering

## License

Internal tool for ACMARKETING.
