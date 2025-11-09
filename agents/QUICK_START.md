# Maestro Docker Swarm - Quick Start Guide

Get Maestro up and running in 5 minutes!

## Prerequisites

- Docker installed (20.10+)
- Docker Swarm initialized
- API keys for Anthropic and Google

## Quick Setup

### 1. Initialize Docker Swarm (if not already done)

```bash
docker swarm init
```

### 2. Configure Environment

```bash
# From the Maestro root directory
cd /path/to/Maestro

# Copy environment template
cp .env.docker .env

# Edit with your API keys
nano .env
```

**Required variables in `.env`:**
```bash
ANTHROPIC_API_KEY=your_actual_key_here
GOOGLE_API_KEY=your_actual_key_here
```

### 3. Prepare Data Directory

```bash
# Create vault directory for Local RAG
mkdir -p data/vault

# Optional: Add your Obsidian vault files
# cp -r /path/to/your/vault/* data/vault/
```

### 4. Build Images

```bash
# Build all Docker images (takes 5-10 minutes)
docker-compose -f docker-stack.yml build
```

### 5. Deploy Stack

```bash
# Deploy all services
docker stack deploy -c docker-stack.yml maestro
```

### 6. Verify Deployment

```bash
# Check all services are running (wait ~30 seconds for startup)
docker stack services maestro

# All services should show 2/2 replicas
```

### 7. Test Services

*Bash/curl:*
```bash
# Test health endpoints
curl http://localhost:8000/health  # Evaluation API
curl http://localhost:8001/health  # Local RAG
curl http://localhost:8002/health  # Path Mapping
curl http://localhost:8003/health  # Supervisor
curl http://localhost:8004/health  # Skills

# All should return: {"status":"healthy"}
```

*PowerShell:*
```powershell
# Test all health endpoints
$services = @(
    @{Name="Evaluation API"; Port=8000},
    @{Name="Local RAG"; Port=8001},
    @{Name="Path Mapping"; Port=8002},
    @{Name="Supervisor"; Port=8003},
    @{Name="Skills"; Port=8004}
)

foreach ($service in $services) {
    Write-Host "$($service.Name) (port $($service.Port)): " -NoNewline
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$($service.Port)/health"
        if ($response.status -eq "healthy") {
            Write-Host "✓ $($response.status)" -ForegroundColor Green
        } else {
            Write-Host "✗ $($response.status)" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ Failed" -ForegroundColor Red
    }
}
```

## Service URLs

Once deployed, access services at:

| Service | URL | Description |
|---------|-----|-------------|
| Evaluation API | http://localhost:8000 | LLM evaluation & scoring |
| Local RAG | http://localhost:8001 | Document retrieval with multi-provider LLM support |
| Path Mapping | http://localhost:8002 | Path translation between systems |
| Supervisor | http://localhost:8003 | Task orchestration with intelligent routing |
| Skills | http://localhost:8004 | LLM-agnostic skill execution |

**All APIs support:**
- LLM provider selection (`local`, `claude`, `gemini`, `openai`)
- Model tier selection (`fast`, `standard`, `premium`)
- Privacy-aware data sensitivity levels (`low`, `medium`, `high`)

## Quick Tests

### Test Supervisor Agent

**Basic Task Execution:**

*Bash/curl:*
```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Hello, test the system",
    "sensitivity": "low",
    "task_type": "synthesis"
  }'
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:8003/execute' `
  -Headers @{'Content-Type'='application/json'} `
  -Body '{"query": "Hello, test the system", "sensitivity": "low", "task_type": "synthesis"}' `
  | ConvertTo-Json -Depth 10
```

**With LLM Provider & Model Selection:**

*Bash/curl:*
```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze my project data",
    "sensitivity": "medium",
    "task_type": "synthesis",
    "llm_provider": "local",
    "model_tier": "premium"
  }'
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:8003/execute' `
  -Headers @{'Content-Type'='application/json'} `
  -Body (ConvertTo-Json @{
    query = "Analyze my project data"
    sensitivity = "medium"
    task_type = "synthesis"
    llm_provider = "local"
    model_tier = "premium"
  }) | ConvertTo-Json -Depth 10
```

**Testing Privacy Warnings:**

*Bash/curl:*
```bash
# Cloud provider + high sensitivity = privacy warning
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize confidential data",
    "sensitivity": "high",
    "llm_provider": "claude",
    "model_tier": "standard"
  }'
```

*PowerShell (formatted output):*
```powershell
# Cloud provider + high sensitivity = privacy warning
Invoke-RestMethod -Method POST -Uri 'http://localhost:8003/execute' `
  -Headers @{'Content-Type'='application/json'} `
  -Body (ConvertTo-Json @{
    query = "Summarize confidential data"
    sensitivity = "high"
    llm_provider = "claude"
    model_tier = "standard"
  }) | ConvertTo-Json -Depth 10
```

### Test Local RAG

**Basic Query (Default Settings):**

*Bash/curl:*
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is in my knowledge base?",
    "top_k": 3
  }'
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:8001/query' `
  -Headers @{'Content-Type'='application/json'} `
  -Body (ConvertTo-Json @{
    query = "What is in my knowledge base?"
    top_k = 3
  }) | ConvertTo-Json -Depth 10
```

**With LLM Provider Selection:**

*Bash/curl:*
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is in my knowledge base?",
    "top_k": 3,
    "llm_provider": "local",
    "model_tier": "standard",
    "sensitivity": "high"
  }'
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:8001/query' `
  -Headers @{'Content-Type'='application/json'} `
  -Body (ConvertTo-Json @{
    query = "What is in my knowledge base?"
    top_k = 3
    llm_provider = "local"
    model_tier = "standard"
    sensitivity = "high"
  }) | ConvertTo-Json -Depth 10
```

**Available Options:**
- **Providers:** `local`, `claude`, `gemini`, `openai`
- **Tiers:** `fast`, `standard`, `premium`
- **Sensitivity:** `low`, `medium`, `high`

### List Available Skills

*Bash/curl:*
```bash
curl http://localhost:8004/skills
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Uri 'http://localhost:8004/skills' | ConvertTo-Json -Depth 10
```

### Test Skills API with LLM Selection

*Bash/curl:*
```bash
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "GenerateProjectSynthesis",
    "parameters": {
      "project_name": "Project Nexus",
      "context": "Testing skill execution"
    },
    "llm_provider": "local",
    "model_tier": "standard",
    "sensitivity": "low"
  }'
```

*PowerShell (formatted output):*
```powershell
Invoke-RestMethod -Method POST -Uri 'http://localhost:8004/execute' `
  -Headers @{'Content-Type'='application/json'} `
  -Body (ConvertTo-Json @{
    skill_name = "GenerateProjectSynthesis"
    parameters = @{
      project_name = "Project Nexus"
      context = "Testing skill execution"
    }
    llm_provider = "local"
    model_tier = "standard"
    sensitivity = "low"
  } -Depth 10) | ConvertTo-Json -Depth 10
```

## LLM Provider Selection

Maestro supports multiple LLM providers with tiered models:

### Available Providers

| Provider | Privacy | Requirements | Models |
|----------|---------|--------------|--------|
| **local** | Maximum (on-device) | Ollama running on localhost:11434 | llama2, llama2:7b, llama2:13b |
| **claude** | Cloud-based | `ANTHROPIC_API_KEY` | claude-3-haiku, claude-3-5-sonnet, claude-3-5-opus |
| **gemini** | Cloud-based | `GOOGLE_API_KEY` | gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp |
| **openai** | Cloud-based | `OPENAI_API_KEY` | gpt-3.5-turbo, gpt-4o |

### Model Tiers

- **fast**: Quick responses, lower cost, good for simple queries
- **standard**: Balanced performance (default)
- **premium**: Best quality, higher cost, complex analysis

### Privacy Features

The system automatically generates warnings when using cloud providers with sensitive data:

- **High sensitivity + cloud provider** → ⚠️ Warning with recommendation to use local
- **Medium sensitivity + cloud provider** → ℹ️ Note about external processing
- **Local provider** → No warnings regardless of sensitivity

### Using PowerShell Test Script

Run comprehensive tests across all providers and tiers:

```powershell
# From project root
.\test-api.ps1

# With verbose output
.\test-api.ps1 -Verbose

# Skip API key error tests
.\test-api.ps1 -SkipErrors
```

This runs ~71 tests covering all provider/tier combinations.

**📚 Full Documentation:** See `/docs/llm-provider-selection.md` for detailed API documentation, examples, and error handling.

## Common Commands

### View Logs

```bash
# View logs for a specific service
docker service logs maestro_supervisor

# Follow logs in real-time
docker service logs -f maestro_local-rag
```

### Restart Services

```bash
# Restart a single service
docker service update --force maestro_supervisor

# Restart all services
docker stack deploy -c docker-stack.yml maestro
```

### Scale Services

```bash
# Scale supervisor to 5 replicas
docker service scale maestro_supervisor=5

# Scale back to 2
docker service scale maestro_supervisor=2
```

### Stop Everything

```bash
# Remove entire stack
docker stack rm maestro

# Verify removal
docker stack ls
```

## Troubleshooting

### Services Not Starting?

```bash
# Check service status
docker service ps maestro_supervisor --no-trunc

# View detailed logs
docker service logs maestro_supervisor
```

### Health Checks Failing?

```bash
# Exec into container
docker exec -it $(docker ps -q -f name=maestro_supervisor) bash

# Check environment variables
env | grep API_KEY

# Test health manually
curl http://localhost:8003/health
```

### Port Already in Use?

```bash
# Find what's using the port
sudo lsof -i :8003

# Kill the process or change ports in docker-stack.yml
```

### Can't Connect to API?

```bash
# Check if service is running
docker service ps maestro_supervisor

# Check network
docker network inspect maestro_maestro-network

# Test from inside another container
docker exec -it $(docker ps -q -f name=maestro_supervisor) \
  curl http://local-rag:8001/health
```

## Next Steps

✅ **Read the full documentation**:
   - Deployment: `/agents/DOCKER_SWARM_DEPLOYMENT.md`
   - LLM Provider Selection: `/docs/llm-provider-selection.md`

✅ **Configure LLM providers**: Set up API keys for Claude, Gemini, or OpenAI

✅ **Test provider selection**: Run `.\test-api.ps1` to verify all providers

✅ **Add your data**: Copy your Obsidian vault to `data/vault/`

✅ **Configure monitoring**: Set up health check dashboards

✅ **Set up backups**: See backup section in full docs

## Architecture Diagram

```
User → Supervisor (8003) → Routes to:
        ├── Local RAG (8001) [Privacy-sensitive tasks]
        ├── Skills (8004) [Tool definitions]
        ├── Path Mapping (8002) [Path translations]
        └── Cloud APIs (Claude/Gemini) [Complex tasks]
```

## Performance Tips

1. **Increase replicas** for high-load services:
   ```bash
   docker service scale maestro_supervisor=5
   ```

2. **Allocate more resources** in `docker-stack.yml`:
   ```yaml
   resources:
     limits:
       cpus: '2.0'
       memory: 4G
   ```

3. **Use SSD storage** for volumes (especially RAG index)

4. **Enable caching** for repeated queries

## Security Checklist

- [ ] API keys stored securely in `.env` (not committed to git)
- [ ] `.env` added to `.gitignore`
- [ ] Services only accessible via reverse proxy in production
- [ ] SSL/TLS enabled for external access
- [ ] Regular backups configured
- [ ] Images scanned for vulnerabilities

## Success Indicators

Your deployment is successful when:

✅ All 5 services show 2/2 replicas
✅ All health endpoints return `{"status":"healthy"}`
✅ Supervisor can communicate with all agents
✅ API requests return valid responses
✅ Logs show no critical errors

---

**Need more details?** See the comprehensive guide: `/agents/DOCKER_SWARM_DEPLOYMENT.md`

**Issues?** Check logs with `docker service logs maestro_<service>`

**Questions?** Open an issue on GitHub
