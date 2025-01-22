# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    DEFAULT_PORT=8000

# Set working directory
WORKDIR /app

# Install only the necessary system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create start script
RUN echo '#!/bin/sh\n\
\n\
# Validate required environment variables\n\
if [ "$ENVIRONMENT" = "production" ]; then\n\
    if [ -z "$OPENAI_API_KEY" ]; then\n\
        echo "Error: OPENAI_API_KEY is required in production"\n\
        exit 1\n\
    fi\n\
    if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then\n\
        echo "Error: SUPABASE_URL and SUPABASE_KEY are required in production"\n\
        exit 1\n\
    fi\n\
    if [ -z "$WHATSAPP_API_TOKEN" ]; then\n\
        echo "Error: WHATSAPP_API_TOKEN is required in production"\n\
        exit 1\n\
    fi\n\
fi\n\
\n\
# Handle PORT environment variable\n\
if [ -z "$PORT" ]; then\n\
    echo "PORT not set, using default: $DEFAULT_PORT"\n\
    export PORT=$DEFAULT_PORT\n\
else\n\
    # Validate that PORT is a number\n\
    if ! echo "$PORT" | grep -E "^[0-9]+$" > /dev/null; then\n\
        echo "Error: PORT must be a number, got: $PORT"\n\
        exit 1\n\
    fi\n\
fi\n\
\n\
echo "Starting server on port: $PORT"\n\
\n\
# Start the application\n\
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT\n\
' > /app/start.sh && chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]
