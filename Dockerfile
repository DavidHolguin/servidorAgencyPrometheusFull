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
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]
