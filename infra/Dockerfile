FROM python:3.11-slim
WORKDIR /app
RUN pip install mcpo uv
CMD ["uvx", "mcpo", "--host", "0.0.0.0", "--port", "8002", "--api-key", "top-secret", "--", "uvx", "mcp-server-time", "--local-timezone=America/Chicago"]