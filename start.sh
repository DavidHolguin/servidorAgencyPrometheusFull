#!/bin/sh

# Validate required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set"
    exit 1
fi

# Set default port if not provided
PORT="${PORT:-8000}"

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
