#!/bin/bash

# Navigate to project
cd ~/acmarketing_scraper

# Start Flask dashboard
python3 dashboard.py > /tmp/acmarketing_dashboard.log 2>&1 &
DASH_PID=$!
echo $DASH_PID > /tmp/dashboard.pid

# Give dashboard time to start
sleep 2

# Start ngrok
ngrok http 5000 > /tmp/acmarketing_ngrok.log 2>&1 &
NGROK_PID=$!
echo $NGROK_PID > /tmp/ngrok.pid

# Log startup
echo "Dashboard started (PID: $DASH_PID)" >> /tmp/acmarketing_startup.log
echo "Ngrok started (PID: $NGROK_PID)" >> /tmp/acmarketing_startup.log
