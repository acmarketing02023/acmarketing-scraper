#!/bin/bash

# ACMARKETING Lead Scraper - Cron-friendly runner
# This script can be called from cron to run the scraper and export results

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting scraper..."

# Run scraper
python cli.py scrape

# Export results
EXPORT_FILE="leads_$(date +%Y%m%d_%H%M%S).csv"
python cli.py export --output "$EXPORT_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Scraper complete. Results: $EXPORT_FILE"
