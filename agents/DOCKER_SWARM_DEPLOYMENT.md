# Maestro Docker Swarm Deployment Guide

This guide provides comprehensive instructions for deploying the Maestro AI Executive Assistant platform using Docker Swarm.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Building Docker Images](#building-docker-images)
5. [Deploying the Stack](#deploying-the-stack)
6. [Service Management](#service-management)
7. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
8. [Scaling Services](#scaling-services)
9. [Updating Services](#updating-services)
10. [Backup and Recovery](#backup-and-recovery)
11. [Security Considerations](#security-considerations)

---

## Architecture Overview

### Services

The Maestro platform consists of 5 microservices:

| Service | Port | Description | Replicas |
|---------|------|-------------|----------|
| **evaluation-api** | 8000 | LLM evaluation and scorecard service | 2 |
| **local-rag** | 8001 | Privacy-first document retrieval and indexing | 2 |
| **path-mapping** | 8002 | Local ↔ Cloud path translation service | 2 |
| **supervisor** | 8003 | Multi-LLM orchestration and task routing | 2 |
| **skills** | 8004 | LLM-agnostic skill abstraction layer | 2 |

### Network Architecture

```
┌────────────────────────────────────────────────┐
│              External Access                    │
│   (Host Machine: localhost:8000-8004)          │
└────────────────┬───────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────┐
│          Docker Swarm Overlay Network          │
│              (maestro-network)                  │
│         Subnet: 10.0.9.0/24                    │
└────────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────────┐
    │            │            │                  │
┌───▼───┐  ┌────▼────┐  ┌────▼─────┐  ┌────────▼────┐
│ Local │  │  Path   │  │Supervisor│  │   Skills    │
│  RAG  │  │ Mapping │  │  Agent   │  │ Abstraction │
│ :8001 │  │  :8002  │  │  :8003   │  │   :8004     │
└───────┘  └─────────┘  └──────────┘  └─────────────┘
```

---

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **CPU**: Minimum 4 cores (8+ cores recommended for production)
- **RAM**: Minimum 8GB (16GB+ recommended for production)
- **Disk Space**: Minimum 20GB free space
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 1.29 or later

### Software Installation

#### Install Docker (Ubuntu/Debian)

```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

#### Initialize Docker Swarm

```bash
# Initialize Swarm mode (creates a single-node swarm)
docker swarm init

# If you have multiple network interfaces, specify the advertise address:
docker swarm init --advertise-addr <YOUR_IP_ADDRESS>
```

#### Verify Installation

```bash
# Check Docker version
docker --version

# Check Swarm status
docker info | grep Swarm

# Should output: Swarm: active
```

---

## Initial Setup

### 1. Clone the Repository (if not already done)

```bash
git clone https://github.com/yourusername/Maestro.git
cd Maestro
```

### 2. Configure Environment Variables

```bash
# Copy the Docker environment template
cp .env.docker .env

# Edit the .env file with your actual API keys
nano .env
```

**Required Environment Variables:**

```bash
# MUST HAVE - API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXX
OPENAI_API_KEY=sk-xxxxxxxxxxxx  # Optional

# Local RAG Configuration
VAULT_HOST_PATH=./data/vault  # Path to your Obsidian vault on host

# Optional - Evaluation Service
NUM_PROMPTS=1
RUNS_PER_PROMPT=1
```

### 3. Prepare Data Directories

```bash
# Create necessary directories
mkdir -p data/vault
mkdir -p data/mappings

# If you have an Obsidian vault, copy or symlink it
# cp -r /path/to/your/obsidian/vault/* data/vault/
# OR
# ln -s /path/to/your/obsidian/vault data/vault
```

---

## Building Docker Images

### Option 1: Build All Images at Once

```bash
# Build all images (recommended for first-time setup)
docker-compose -f docker-stack.yml build
```

### Option 2: Build Individual Services

```bash
# Build evaluation API
docker build -t maestro/evaluation-api:latest -f Dockerfile .

# Build Local RAG
docker build -t maestro/local-rag:latest -f agents/local_rag/Dockerfile agents/local_rag/

# Build Path Mapping
docker build -t maestro/path-mapping:latest -f agents/cloud_integration/Dockerfile agents/cloud_integration/

# Build Supervisor
docker build -t maestro/supervisor:latest -f agents/orchestrator/Dockerfile agents/orchestrator/

# Build Skills
docker build -t maestro/skills:latest -f agents/abstraction_layer/Dockerfile agents/abstraction_layer/
```

### Verify Images

```bash
# List all Maestro images
docker images | grep maestro
```

---

## Deploying the Stack

### Deploy All Services

```bash
# Deploy the entire stack
docker stack deploy -c docker-stack.yml maestro

# This command will:
# 1. Create the overlay network (maestro-network)
# 2. Create all volumes
# 3. Deploy all 5 services with 2 replicas each
# 4. Set up health checks and restart policies
```

### Verify Deployment

```bash
# List all stacks
docker stack ls

# List services in the maestro stack
docker stack services maestro

# Expected output:
# ID             NAME                    MODE         REPLICAS   IMAGE
# xxxxx          maestro_evaluation-api  replicated   2/2        maestro/evaluation-api:latest
# xxxxx          maestro_local-rag       replicated   2/2        maestro/local-rag:latest
# xxxxx          maestro_path-mapping    replicated   2/2        maestro/path-mapping:latest
# xxxxx          maestro_supervisor      replicated   2/2        maestro/supervisor:latest
# xxxxx          maestro_skills          replicated   2/2        maestro/skills:latest
```

### Check Service Status

```bash
# View detailed service information
docker service ps maestro_supervisor

# Check logs for a specific service
docker service logs maestro_supervisor

# Follow logs in real-time
docker service logs -f maestro_local-rag
```

---

## Service Management

### Access Service APIs

Once deployed, services are accessible at:

- **Evaluation API**: http://localhost:8000
- **Local RAG**: http://localhost:8001
- **Path Mapping**: http://localhost:8002
- **Supervisor**: http://localhost:8003
- **Skills**: http://localhost:8004

### Test Health Endpoints

```bash
# Test all health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health

# All should return: {"status":"healthy","service":"<service-name>"}
```

### Example API Calls

#### Query Local RAG

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of the system?",
    "top_k": 5
  }'
```

#### List Available Skills

```bash
curl http://localhost:8004/skills
```

#### Execute Task via Supervisor

```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize my recent project notes",
    "sensitivity": "high",
    "task_type": "synthesis"
  }'
```

#### Check Agent Status

```bash
curl http://localhost:8003/agents
```

---

## Monitoring and Troubleshooting

### Monitor Service Health

```bash
# Check all services status
docker stack services maestro

# Inspect a specific service
docker service inspect maestro_supervisor --pretty

# View service logs
docker service logs maestro_supervisor --tail 100
```

### Common Issues and Solutions

#### Issue 1: Service Not Starting

```bash
# Check service logs
docker service logs maestro_<service-name>

# Check if ports are already in use
sudo netstat -tulpn | grep <PORT>

# Inspect service for errors
docker service inspect maestro_<service-name>
```

#### Issue 2: Health Check Failing

```bash
# Exec into a running container
docker exec -it $(docker ps -q -f name=maestro_supervisor) bash

# Manually test health check
curl http://localhost:8003/health

# Check environment variables
env | grep API_KEY
```

#### Issue 3: Network Issues Between Services

```bash
# Inspect network
docker network inspect maestro_maestro-network

# Test connectivity from supervisor to local-rag
docker exec -it $(docker ps -q -f name=maestro_supervisor) \
  curl http://local-rag:8001/health
```

#### Issue 4: Volume Permissions

```bash
# Check volume mounts
docker volume ls
docker volume inspect maestro_rag-data

# If permission issues, adjust on host:
sudo chown -R 1000:1000 data/vault
```

### Restart Services

```bash
# Restart a single service
docker service update --force maestro_supervisor

# Restart all services
docker stack deploy -c docker-stack.yml maestro
```

### Remove and Redeploy

```bash
# Remove the entire stack
docker stack rm maestro

# Wait for removal to complete (check with 'docker stack ls')
# Then redeploy
docker stack deploy -c docker-stack.yml maestro
```

---

## Scaling Services

### Scale Up

```bash
# Scale a specific service to 5 replicas
docker service scale maestro_supervisor=5

# Scale multiple services at once
docker service scale \
  maestro_local-rag=4 \
  maestro_supervisor=3 \
  maestro_skills=3
```

### Scale Down

```bash
# Scale back to 1 replica (development mode)
docker service scale maestro_supervisor=1
```

### Auto-Scaling Considerations

For production deployments, consider:

1. **Load Balancing**: Swarm automatically load balances across replicas
2. **Resource Limits**: Set in `docker-stack.yml` under `resources`
3. **Horizontal Pod Autoscaling**: Requires external orchestration (Kubernetes recommended for advanced auto-scaling)

---

## Updating Services

### Rolling Updates

```bash
# Update service with new image (zero-downtime)
docker service update --image maestro/supervisor:v2.0 maestro_supervisor

# Update with environment variable change
docker service update --env-add NEW_VAR=value maestro_supervisor

# Update resource limits
docker service update --limit-memory 4G maestro_local-rag
```

### Blue-Green Deployment

```bash
# 1. Build new version with different tag
docker build -t maestro/supervisor:v2.0 -f agents/orchestrator/Dockerfile agents/orchestrator/

# 2. Update service (Swarm performs rolling update automatically)
docker service update --image maestro/supervisor:v2.0 maestro_supervisor

# 3. Rollback if needed
docker service rollback maestro_supervisor
```

---

## Backup and Recovery

### Backup Volumes

```bash
# Create backup directory
mkdir -p backups

# Backup RAG data
docker run --rm \
  -v maestro_rag-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/rag-data-$(date +%Y%m%d).tar.gz /data

# Backup path mappings
docker run --rm \
  -v maestro_mapping-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/mapping-data-$(date +%Y%m%d).tar.gz /data
```

### Restore Volumes

```bash
# Restore RAG data
docker run --rm \
  -v maestro_rag-data:/data \
  -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/rag-data-20240101.tar.gz -C /

# Restart service after restore
docker service update --force maestro_local-rag
```

### Backup Configuration

```bash
# Backup .env file
cp .env backups/.env.$(date +%Y%m%d)

# Backup docker-stack.yml
cp docker-stack.yml backups/docker-stack.yml.$(date +%Y%m%d)
```

---

## Security Considerations

### 1. API Key Management

```bash
# NEVER commit .env to version control
echo ".env" >> .gitignore

# Use Docker secrets for production (more secure)
echo "your_anthropic_key" | docker secret create anthropic_api_key -

# Update docker-stack.yml to use secrets:
# secrets:
#   - anthropic_api_key
```

### 2. Network Security

```bash
# Restrict external access (only allow from specific IPs)
# Use a reverse proxy (nginx/traefik) with SSL

# Internal services should NOT be exposed externally
# Modify docker-stack.yml to remove 'ports:' for internal services
```

### 3. Container Security

```bash
# Run containers as non-root user
# Add to Dockerfile:
# USER 1000:1000

# Scan images for vulnerabilities
docker scan maestro/supervisor:latest
```

### 4. Regular Updates

```bash
# Keep base images updated
docker pull python:3.11-slim

# Rebuild images regularly
docker-compose -f docker-stack.yml build --no-cache
```

---

## Advanced Configuration

### Multi-Node Swarm

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER-IP>

# On worker nodes, run the command provided by init:
docker swarm join --token <TOKEN> <MANAGER-IP>:2377

# Verify nodes
docker node ls
```

### Custom Network Configuration

Edit `docker-stack.yml`:

```yaml
networks:
  maestro-network:
    driver: overlay
    attachable: true
    driver_opts:
      encrypted: "true"  # Enable encryption
    ipam:
      config:
        - subnet: 10.0.9.0/24
          gateway: 10.0.9.1
```

### Logging Configuration

```bash
# Configure logging driver in docker-stack.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# Or use external logging (ELK, Splunk)
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logstash:5000"
```

---

## Quick Reference Commands

### Deployment

```bash
docker stack deploy -c docker-stack.yml maestro        # Deploy stack
docker stack rm maestro                                # Remove stack
docker stack ls                                        # List stacks
docker stack services maestro                          # List services
```

### Service Management

```bash
docker service ls                                      # List all services
docker service ps maestro_supervisor                   # Service tasks
docker service logs maestro_supervisor                 # Service logs
docker service scale maestro_supervisor=3              # Scale service
docker service update --force maestro_supervisor       # Restart service
```

### Troubleshooting

```bash
docker service ps --no-trunc maestro_supervisor        # Full error messages
docker service inspect maestro_supervisor --pretty     # Service config
docker exec -it <container-id> bash                    # Enter container
docker logs <container-id>                             # Container logs
```

### Cleanup

```bash
docker stack rm maestro                                # Remove stack
docker system prune -a                                 # Clean all unused data
docker volume prune                                    # Remove unused volumes
```

---

## Getting Help

### Documentation

- Docker Swarm: https://docs.docker.com/engine/swarm/
- Docker Compose: https://docs.docker.com/compose/
- FastAPI: https://fastapi.tiangolo.com/

### Troubleshooting

If you encounter issues:

1. Check service logs: `docker service logs maestro_<service>`
2. Verify environment variables: `docker exec <container> env`
3. Test health endpoints: `curl http://localhost:<port>/health`
4. Check network connectivity between services
5. Verify volumes are correctly mounted

### Support

For issues specific to Maestro:
- Check GitHub Issues
- Review service-specific README files in `agents/` directories

---

## Next Steps

After successful deployment:

1. ✅ Test all health endpoints
2. ✅ Verify inter-service communication
3. ✅ Run sample queries against each service
4. ✅ Set up monitoring and alerting
5. ✅ Configure backups
6. ✅ Implement SSL/TLS for production
7. ✅ Set up CI/CD pipeline for updates

---

**Last Updated**: 2024
**Version**: 1.0.0
**Maintainer**: Maestro Team
