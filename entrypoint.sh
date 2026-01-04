#!/bin/sh

# Use PORT from environment, default to 5000
PORT="${PORT:-5000}"

echo "Starting Manga Heaven on port $PORT"

# Start Gunicorn
exec gunicorn --bind "0.0.0.0:$PORT" --workers 2 --timeout 120 web.app:app
