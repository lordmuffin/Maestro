# Dockerfile for Maestro Evaluation Service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scorecard.py .
COPY baseline.py .
COPY metrics.py .
COPY kpis.py .
COPY sensitivity.py .
COPY evaluation_pipeline.py .
COPY tracking.py .
COPY prompts/ ./prompts/
COPY api.py .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the API
CMD ["python", "api.py"]
