# Phase 2: Cloud Knowledge Integration Guide

## Overview

Phase 2 extends Maestro with cloud integration capabilities, enabling hybrid RAG that combines local privacy with cloud accessibility. This phase introduces:

- **Path Mapping Service**: Bidirectional mapping between local and cloud file paths
- **Google Drive Integration**: Access and search cloud-synced files
- **Gemini Integration**: Cloud-based LLM for synthesis with cloud data
- **Cloud RAG**: Semantic search and query across Google Drive files

## Prerequisites

Before using Phase 2 features, you need:

1. **Google Cloud Project** with Drive API enabled
2. **Service Account** with Drive access
3. **Gemini API Key** for cloud LLM access
4. **Google Drive folder** with synced Obsidian vault (optional)

## Configuration

### 1. Google Cloud Setup

Create a service account and download credentials:

```bash
# Enable Google Drive API
gcloud services enable drive.googleapis.com

# Create service account
gcloud iam service-accounts create maestro-service \
    --display-name="Maestro Service Account"

# Create and download key
gcloud iam service-accounts keys create credentials/google-credentials.json \
    --iam-account=maestro-service@PROJECT_ID.iam.gserviceaccount.com
```

### 2. Environment Configuration

Update your `.env` file:

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id

# Google Gemini
GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here
```

### 3. Mount Credentials

Ensure your credentials are mounted in docker-compose.yml:

```yaml
services:
  backend:
    volumes:
      - ./credentials:/app/credentials:ro
```

## Features

### Path Mapping Service

The Path Mapping Service maintains bidirectional mappings between local and cloud files, resolving the "path mangling" issue that occurs with sync plugins.

#### Create a Path Mapping

```bash
curl -X POST http://localhost:8000/api/v1/path-mapping \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/app/data/vault/Projects/Maestro/Overview.md",
    "cloud_path": "Projects_Maestro_Overview.md",
    "cloud_id": "1abc123def456",
    "cloud_provider": "google_drive",
    "file_type": "markdown"
  }'
```

#### Resolve Local to Cloud

```bash
# Get cloud location for local file
curl http://localhost:8000/api/v1/path-mapping/resolve/local/app/data/vault/test.md
```

Response:
```json
{
  "cloud_path": "test.md",
  "cloud_id": "1abc123",
  "provider": "google_drive"
}
```

#### Sync Entire Vault

Automatically create mappings for all files in your vault:

```bash
curl -X POST http://localhost:8000/api/v1/path-mapping/sync \
  -H "Content-Type: application/json" \
  -d '{
    "vault_path": "/app/data/vault",
    "gdrive_folder_id": "your-folder-id"
  }'
```

### Cloud RAG

Query your Google Drive files using semantic search powered by Gemini.

#### Hybrid Search

Search Drive and get AI-synthesized answers:

```bash
curl -X POST http://localhost:8000/api/v1/cloud-rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key points from the Q4 strategy document?",
    "folder_id": "optional-folder-id",
    "max_results": 5
  }'
```

Response:
```json
{
  "response": "Based on the Q4 strategy documents, the key points are...",
  "sources": [
    {
      "file_id": "1abc123",
      "file_name": "Q4-Strategy.md"
    }
  ],
  "query": "What are the key points..."
}
```

#### Search Files

Search for files without synthesis:

```bash
curl -X POST http://localhost:8000/api/v1/cloud-rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "budget spreadsheet",
    "folder_id": "optional-folder-id",
    "max_results": 10
  }'
```

#### Query Specific Files

Query with explicit file IDs:

```bash
curl -X POST http://localhost:8000/api/v1/cloud-rag/query-files \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize these documents",
    "file_ids": ["1abc123", "2def456", "3ghi789"]
  }'
```

### Check Cloud RAG Status

Verify your cloud integration is properly configured:

```bash
curl http://localhost:8000/api/v1/cloud-rag/status
```

Response:
```json
{
  "initialized": true,
  "google_credentials_configured": true,
  "gemini_api_key_configured": true
}
```

## Architecture

### Hybrid RAG Flow

```
User Query
    ↓
Supervisor Agent (classifies query)
    ├─ Sensitive data? → Local RAG (Obsidian + Ollama)
    └─ Cloud data? → Cloud RAG (Drive + Gemini)
    ↓
Path Mapping Service (resolves file locations)
    ↓
Response with sources
```

### Data Privacy

**Local-First Guarantee**:
- Queries classified as "sensitive" never touch cloud APIs
- Local RAG uses only local Ollama and vault files
- Path mappings are stored locally in PostgreSQL

**Cloud Access**:
- Only used when explicitly requested or auto-classified as non-sensitive
- Service account credentials never exposed to frontend
- All Drive API calls logged for audit

## Use Cases

### 1. Cross-Workspace Search

Search across local Obsidian notes AND cloud Google Docs:

```python
# In your application
response = requests.post(
    "http://localhost:8000/api/v1/cloud-rag/query",
    json={
        "query": "Find all mentions of Project Phoenix",
        "folder_id": "workspace-folder-id"
    }
)
```

### 2. Vault Synchronization

Keep path mappings in sync after Drive sync:

```bash
# Run periodically via cron
curl -X POST http://localhost:8000/api/v1/path-mapping/sync \
  -H "Content-Type: application/json" \
  -d '{
    "vault_path": "/app/data/vault",
    "gdrive_folder_id": "folder-id"
  }'
```

### 3. Hybrid Context

Query using both local and cloud context:

```python
# Get local context
local_response = requests.post(
    "http://localhost:8000/api/v1/rag/query",
    json={"query": "Local notes about Project X"}
)

# Get cloud context
cloud_response = requests.post(
    "http://localhost:8000/api/v1/cloud-rag/query",
    json={"query": "Cloud docs about Project X"}
)

# Combine responses for full context
```

## Troubleshooting

### Cloud RAG Not Initialized

**Problem**: `/api/v1/cloud-rag/query` returns 503

**Solution**:
1. Check `/api/v1/cloud-rag/status`
2. Verify credentials file exists and is mounted
3. Verify `GOOGLE_GEMINI_API_KEY` is set
4. Check backend logs: `docker-compose logs backend`

### Permission Denied on Drive API

**Problem**: Drive API returns 403

**Solution**:
1. Verify service account has access to target folder
2. Share Drive folder with service account email
3. Check API is enabled: `gcloud services list | grep drive`

### Path Mapping Not Found

**Problem**: `/resolve/local/...` returns 404

**Solution**:
1. Run vault sync: `POST /api/v1/path-mapping/sync`
2. Manually create mapping: `POST /api/v1/path-mapping`
3. Check vault path is correct

## Next Steps

After completing Phase 2 setup:

1. **Phase 3**: Multi-LLM Orchestration with LangGraph
2. **Test Hybrid Queries**: Try queries that span local and cloud
3. **Monitor Usage**: Check Cloud RAG query logs
4. **Optimize**: Adjust `max_results` for performance

## API Reference

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Considerations

1. **Credentials**: Never commit `credentials/` to git
2. **API Keys**: Rotate Gemini API keys regularly
3. **Service Account**: Use principle of least privilege
4. **Audit Logs**: Monitor all Cloud RAG queries
5. **Data Residency**: Be aware of where Gemini processes data

## Support

For issues with Phase 2:
- Check logs: `docker-compose logs -f backend`
- Review configuration: `/api/v1/cloud-rag/status`
- Consult [Troubleshooting Guide](./troubleshooting.md)
