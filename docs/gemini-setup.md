# Quick Start: Using Google Gemini with Local RAG

This guide shows you how to configure the Local RAG agent to use Google Gemini for LLM queries.

## Prerequisites

- Google API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Docker Swarm cluster running

## Setup Steps

### 1. Install Gemini Package

Edit `agents/local_rag/requirements.txt` and uncomment the Gemini line:

```txt
# Optional LLM Integrations (only needed if using specific providers)
# Uncomment the ones you want to use:
# llama-index-llms-ollama>=0.1.0  # For local Ollama
llama-index-llms-gemini>=0.1.0  # For Google Gemini  <-- UNCOMMENT THIS LINE
# llama-index-llms-openai>=0.1.0  # For OpenAI GPT
# llama-index-llms-anthropic>=0.1.0  # For Anthropic Claude
```

### 2. Set Your API Key

```bash
# On Windows (PowerShell)
$env:GOOGLE_API_KEY = "your-api-key-here"

# On Linux/Mac
export GOOGLE_API_KEY=your-api-key-here
```

### 3. Rebuild and Deploy

```bash
# Rebuild the Docker image with Gemini support
docker build -t maestro-local-rag:latest -f agents/local_rag/Dockerfile agents/local_rag

# Update the service
docker service update --image maestro-local-rag:latest --env-add GOOGLE_API_KEY=$GOOGLE_API_KEY --force maestro_local-rag
```

### 4. Verify Configuration

Check the logs to confirm Gemini is being used:

```bash
docker service logs maestro_local-rag | grep "LLM configured"
```

You should see:
```
✓ LLM configured: Google Gemini Pro
```

## Test the Configuration

Send a test query:

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is in my knowledge base?","top_k":3}'
```

## Benefits of Using Gemini

1. **Cost-Effective**: Gemini offers competitive pricing
2. **Fast**: Low latency responses
3. **Capable**: Strong performance on RAG tasks
4. **Free Tier**: Google offers free tier for testing

## Switching Back to Local Mode

To switch back to local-only mode:

1. Remove the GOOGLE_API_KEY environment variable
2. Redeploy the service

The system will automatically fall back to MockLLM (local).

## Troubleshooting

### Issue: "GOOGLE_API_KEY found but llama-index-llms-gemini not installed"

**Solution**: You forgot to uncomment the Gemini line in requirements.txt. Go back to Step 1.

### Issue: API key authentication error

**Solution**: Verify your API key is valid at [Google AI Studio](https://makersuite.google.com/app/apikey)

### Issue: Service not using Gemini

**Solution**: Check that the environment variable is set correctly:
```bash
docker service inspect maestro_local-rag --format='{{json .Spec.TaskTemplate.ContainerSpec.Env}}' | python -m json.tool
```

You should see `GOOGLE_API_KEY` in the list.

## Cost Monitoring

Keep track of your Gemini API usage at [Google Cloud Console](https://console.cloud.google.com/apis/dashboard)

## Model Options

The default configuration uses `gemini-pro`. To use a different model, edit `local_rag_agent.py:415`:

```python
Settings.llm = Gemini(model="models/gemini-pro", temperature=0.1)
```

Available models:
- `models/gemini-pro` - Best for most tasks
- `models/gemini-pro-vision` - For image understanding (future enhancement)

Refer to [Google's model documentation](https://ai.google.dev/models/gemini) for the latest options.
