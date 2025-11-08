# Dockerfile for Path Mapping Service
FROM python:3.11-slim

WORKDIR /app

# Copy application code
COPY path_mapping_service.py .
COPY api.py .

# Install FastAPI and uvicorn
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')" || exit 1

# Run the API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
