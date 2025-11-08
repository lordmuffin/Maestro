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

```bash
# Test health endpoints
curl http://localhost:8000/health  # Evaluation API
curl http://localhost:8001/health  # Local RAG
curl http://localhost:8002/health  # Path Mapping
curl http://localhost:8003/health  # Supervisor
curl http://localhost:8004/health  # Skills

# All should return: {"status":"healthy"}
```

## Service URLs

Once deployed, access services at:

| Service | URL | Description |
|---------|-----|-------------|
| Evaluation API | http://localhost:8000 | LLM evaluation |
| Local RAG | http://localhost:8001 | Document retrieval |
| Path Mapping | http://localhost:8002 | Path translation |
| Supervisor | http://localhost:8003 | Task orchestration |
| Skills | http://localhost:8004 | Skill execution |

## Quick Tests

### Test Supervisor Agent

```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Hello, test the system",
    "sensitivity": "low",
    "task_type": "synthesis"
  }'
```

### Test Local RAG

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is in my knowledge base?",
    "top_k": 3
  }'
```

### List Available Skills

```bash
curl http://localhost:8004/skills
```

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

✅ **Read the full documentation**: `/agents/DOCKER_SWARM_DEPLOYMENT.md`

✅ **Configure monitoring**: Set up health check dashboards

✅ **Add your data**: Copy your Obsidian vault to `data/vault/`

✅ **Test integrations**: Try all API endpoints

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
