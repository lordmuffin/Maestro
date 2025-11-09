# LLM Provider and Model Tier Selection

This guide explains how to select specific LLM providers and model tiers when making API calls to the Maestro system.

## Overview

Maestro supports multiple LLM providers with a tiered model system, allowing you to balance performance, cost, and privacy based on your needs. The system provides:

- **Multiple providers**: Local (Ollama), Claude (Anthropic), Gemini (Google), OpenAI
- **Model tiers**: Fast, Standard, Premium
- **Privacy warnings**: Automatic warnings when using cloud providers with sensitive data
- **Strict validation**: Immediate error feedback for unavailable providers/models

## Supported Providers

### Local Provider (Ollama)
- **Privacy**: Maximum (all processing on-device)
- **Cost**: Free
- **Requirement**: Ollama running on localhost:11434
- **Models**:
  - `fast`: llama2
  - `standard`: llama2:7b
  - `premium`: llama2:13b

### Claude Provider (Anthropic)
- **Privacy**: Cloud-based
- **Requirement**: `ANTHROPIC_API_KEY` environment variable
- **Models**:
  - `fast`: claude-3-haiku-20240307
  - `standard`: claude-3-5-sonnet-20241022
  - `premium`: claude-3-5-opus-20250514

### Gemini Provider (Google)
- **Privacy**: Cloud-based
- **Requirement**: `GOOGLE_API_KEY` environment variable
- **Models**:
  - `fast`: gemini-1.5-flash
  - `standard`: gemini-1.5-pro
  - `premium`: gemini-2.0-flash-exp

### OpenAI Provider
- **Privacy**: Cloud-based
- **Requirement**: `OPENAI_API_KEY` environment variable
- **Models**:
  - `fast`: gpt-3.5-turbo
  - `standard`: gpt-4o
  - `premium`: gpt-4o

## API Usage

### Local RAG API (Port 8001)

**Endpoint**: `POST /query`

**Request Body**:
```json
{
  "query": "What are the key themes in Project Nexus?",
  "top_k": 5,
  "llm_provider": "claude",
  "model_tier": "standard",
  "sensitivity": "medium"
}
```

**Response**:
```json
{
  "status": "success",
  "results": [...],
  "query": "What are the key themes in Project Nexus?",
  "provider_used": "claude",
  "model_used": "claude-3-5-sonnet-20241022",
  "privacy_warning": "ℹ️  Privacy Note: Using cloud provider 'Anthropic Claude' with medium-sensitivity data..."
}
```

### Supervisor API (Port 8003)

**Endpoint**: `POST /execute`

**Request Body**:
```json
{
  "query": "Summarize my recent meetings",
  "sensitivity": "high",
  "task_type": "synthesis",
  "llm_provider": "local",
  "model_tier": "premium"
}
```

**Response**:
```json
{
  "status": "success",
  "result": {...},
  "agent_used": "local_rag",
  "execution_time": 2.5,
  "provider_used": "local",
  "model_used": "llama2:13b",
  "privacy_warning": null
}
```

### Skills API (Port 8004)

**Endpoint**: `POST /execute`

**Request Body**:
```json
{
  "skill_name": "GenerateProjectSynthesis",
  "parameters": {
    "project_name": "Project Nexus",
    "context": "..."
  },
  "llm_provider": "gemini",
  "model_tier": "fast",
  "sensitivity": "low"
}
```

**Response**:
```json
{
  "status": "success",
  "result": {...},
  "skill_name": "GenerateProjectSynthesis",
  "llm_provider": "gemini",
  "model_used": "gemini-1.5-flash",
  "privacy_warning": null
}
```

## Privacy Warnings

The system automatically generates privacy warnings based on data sensitivity and provider choice:

### High Sensitivity + Cloud Provider
```
⚠️  Privacy Warning: Using cloud provider 'Anthropic Claude' with high-sensitivity data.
Consider using 'local' provider for maximum privacy.
```

### Medium Sensitivity + Cloud Provider
```
ℹ️  Privacy Note: Using cloud provider 'Google Gemini' with medium-sensitivity data.
Data will be processed externally.
```

### Low Sensitivity or Local Provider
No warning generated.

## Error Handling

### Provider Unavailable
**Error**: Provider not available (missing API key or service down)

**Example**:
```json
{
  "detail": "Provider 'claude' unavailable: ANTHROPIC_API_KEY not set"
}
```

**Status Code**: 400

### Invalid Provider
**Error**: Requested provider doesn't exist

**Example**:
```json
{
  "detail": "Invalid provider 'gpt4'. Valid providers: local, claude, gemini, openai"
}
```

**Status Code**: 400

### Invalid Model Tier
**Error**: Requested tier doesn't exist for provider

**Example**:
```json
{
  "detail": "Invalid tier 'ultra' for provider 'claude'. Valid tiers: fast, standard, premium"
}
```

**Status Code**: 400

## Default Behavior

When provider or model tier are not specified:

- **Local RAG API**: Defaults to `local` provider with `standard` tier
- **Supervisor API**: Uses intelligent routing based on task type and sensitivity
- **Skills API**: Defaults to `claude` provider with `standard` tier

## Environment Configuration

Set API keys in your `.env` file:

```bash
# Required for Claude provider
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Required for Gemini provider
GOOGLE_API_KEY=your_google_api_key_here

# Required for OpenAI provider
OPENAI_API_KEY=your_openai_api_key_here
```

For local provider (Ollama):
```bash
# Start Ollama service
ollama serve

# Pull models
ollama pull llama2
```

## Model Tier Selection Guidelines

### Fast Tier
- **Use case**: Quick responses, simple queries, high-volume requests
- **Latency**: Lowest
- **Cost**: Lowest
- **Quality**: Good for straightforward tasks

### Standard Tier (Default)
- **Use case**: Most general-purpose queries
- **Latency**: Moderate
- **Cost**: Moderate
- **Quality**: Balanced performance and cost

### Premium Tier
- **Use case**: Complex analysis, critical decisions, high-quality output
- **Latency**: Highest
- **Cost**: Highest
- **Quality**: Best available

## Privacy-First Recommendations

For different data sensitivity levels:

### High Sensitivity (Personal, Confidential, Proprietary)
- ✅ **Recommended**: `local` provider (any tier)
- ⚠️ **Caution**: Cloud providers (will generate warning)

### Medium Sensitivity (Internal, Work-Related)
- ✅ **Acceptable**: Any provider
- ℹ️ **Note**: Cloud providers will note external processing

### Low Sensitivity (Public, General Knowledge)
- ✅ **Recommended**: Any provider based on performance needs
- 💡 **Tip**: Use `fast` tier for cost optimization

## Examples

### Privacy-First Query
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize my confidential meeting notes",
    "llm_provider": "local",
    "model_tier": "premium",
    "sensitivity": "high"
  }'
```

### High-Quality Analysis
```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze market trends and provide strategic recommendations",
    "llm_provider": "claude",
    "model_tier": "premium",
    "sensitivity": "low",
    "task_type": "synthesis"
  }'
```

### Quick Lookup
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "When is my next meeting?",
    "llm_provider": "gemini",
    "model_tier": "fast",
    "sensitivity": "medium"
  }'
```

## Troubleshooting

### "Provider 'local' unavailable"
- Ensure Ollama is running: `ollama serve`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`

### "Provider 'claude' unavailable: ANTHROPIC_API_KEY not set"
- Set the API key in `.env` file
- Restart Docker services: `docker stack deploy -c docker-stack.yml maestro`

### "timeout" errors
- Increase timeout in request
- Use faster model tier
- Check provider service status

## Model Registry Reference

The model registry is defined in `agents/orchestrator/model_registry.py`. You can view available models programmatically:

```python
from model_registry import list_all_models, get_available_providers

# List all models
models = list_all_models()
print(models)

# Check available providers
providers = get_available_providers()
print(f"Available: {providers}")
```

## Backward Compatibility

All new parameters (`llm_provider`, `model_tier`, `sensitivity`) are optional. Existing API calls without these parameters will continue to work with default behavior:

- Existing scripts: ✅ No changes required
- New features: ✅ Opt-in via parameters
- Response format: ✅ Additional fields added (non-breaking)
