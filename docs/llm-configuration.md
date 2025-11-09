# Flexible LLM Configuration for Local RAG Agent

The Local RAG agent now supports flexible LLM configuration based on available API keys. It automatically detects and uses the best available option.

## Priority Order

The system checks for available LLMs in this order:

1. **Ollama (Local)** - No API key needed
2. **Google Gemini** - Requires `GOOGLE_API_KEY`
3. **OpenAI** - Requires `OPENAI_API_KEY`
4. **Anthropic** - Requires `ANTHROPIC_API_KEY`
5. **MockLLM** - Fallback for testing/development

## Current Configuration

Without any API keys configured, the system uses **MockLLM (local fallback)**, which works locally without external API calls.

## How to Configure Different LLMs

### Option 1: Use Ollama (Recommended for Local-First)

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama2`
3. Ensure Ollama is running (it listens on http://localhost:11434)
4. Install the package: `pip install llama-index-llms-ollama`
5. Restart the service - it will automatically detect and use Ollama

### Option 2: Use Google Gemini (Recommended for Cloud)

**Step 1**: Get your Google API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

**Step 2**: Install the Gemini package in the Docker image by uncommenting it in `agents/local_rag/requirements.txt`:
```txt
llama-index-llms-gemini>=0.1.0  # For Google Gemini
```

**Step 3**: Set your API key and redeploy:
```bash
# Set the environment variable
export GOOGLE_API_KEY=your-api-key-here

# Rebuild the image with Gemini support
docker build -t maestro-local-rag:latest -f agents/local_rag/Dockerfile agents/local_rag

# Update the service
docker stack deploy -c docker-stack.yml maestro
```

The system will automatically detect and use Gemini Pro.

### Option 3: Use OpenAI

**Step 1**: Install the OpenAI package in `agents/local_rag/requirements.txt`:
```txt
llama-index-llms-openai>=0.1.0  # For OpenAI GPT
```

**Step 2**: Set your API key and redeploy:
```bash
export OPENAI_API_KEY=your-key-here
docker build -t maestro-local-rag:latest -f agents/local_rag/Dockerfile agents/local_rag
docker stack deploy -c docker-stack.yml maestro
```

### Option 4: Use Anthropic Claude

Update your `docker-stack.yml` to add the API key:

```yaml
services:
  local-rag:
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

Then redeploy:
```bash
export ANTHROPIC_API_KEY=your-key-here
docker stack deploy -c docker-stack.yml maestro
```

## Testing the Configuration

You can test which LLM is being used by checking the logs:

```bash
docker service logs maestro_local-rag | grep "LLM configured"
```

You should see one of:
- `✓ LLM configured: Ollama (local)`
- `✓ LLM configured: Google Gemini Pro`
- `✓ LLM configured: OpenAI GPT-3.5`
- `✓ LLM configured: Anthropic Claude Haiku`
- `✓ LLM configured: MockLLM (local fallback)`

## Benefits of This Approach

1. **Privacy-First**: Defaults to local options (Ollama, MockLLM)
2. **Flexible**: Supports multiple LLM providers
3. **No Hard Dependencies**: Works without any API keys
4. **Cost Control**: Only uses paid APIs when explicitly configured
5. **Environment-Aware**: Automatically detects what's available

## Current Status

Your system is currently running with:
- **LLM**: MockLLM (local fallback)
- **Embeddings**: HuggingFace BGE-small (local)
- **Vector Store**: FAISS (local)
- **Documents Indexed**: 145 documents from your vault

All processing is happening locally with no external API calls.
