# Maestro Deployment Architecture

## Overview

Maestro uses **docker-compose** for orchestration (NOT Docker Swarm). This document explains the current deployment architecture, service dependencies, networking configuration, and deployment best practices.

## Deployment Method: Docker Compose

Maestro is deployed using **docker-compose** located in the `infra/` directory.

### Why Docker Compose (Not Swarm)?

- **Simpler setup**: No cluster initialization required
- **Local development friendly**: Easy to run on developer machines
- **Resource efficient**: Lower overhead than Swarm
- **Sufficient for current scale**: Meets project requirements without complexity

### Docker Compose Version

Maestro supports both Docker Compose V1 and V2:
- **V2** (recommended): `docker compose` (built into Docker Desktop)
- **V1** (legacy): `docker-compose` (separate install)

Check your version:
```bash
docker compose version  # V2
# OR
docker-compose --version  # V1
```

## Architecture Components

### Current Services

#### 1. PostgreSQL Database
- **Image**: `postgres:16-alpine`
- **Container Name**: `maestro-postgres`
- **Port**: 5432 (exposed to host)
- **Purpose**: Primary data store for tasks, mappings, and application state
- **Healthcheck**: `pg_isready` every 10 seconds
- **Volume**: `postgres_data` for persistence

**Configuration**:
```yaml
postgres:
  image: postgres:16-alpine
  container_name: maestro-postgres
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
  ports:
    - "5432:5432"
  networks:
    - maestro-network
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### 2. Backend API (FastAPI)
- **Build Context**: `../backend`
- **Dockerfile**: `../infra/docker/backend/Dockerfile`
- **Container Name**: `maestro-backend`
- **Port**: 8000 (exposed to host)
- **Purpose**: Main application server - API endpoints, RAG, skills
- **Healthcheck**: `curl -f http://localhost:8000/health` every 30 seconds
- **Volumes**:
  - Backend code (development hot-reload)
  - Obsidian vault (read-only mount)
  - Google credentials (if used)

**Dependencies**:
- Waits for PostgreSQL to be healthy
- Connects to host Ollama via `host.docker.internal`

**Configuration**:
```yaml
backend:
  build:
    context: ../backend
    dockerfile: ../infra/docker/backend/Dockerfile
  container_name: maestro-backend
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - OLLAMA_HOST=${OLLAMA_HOST}
    - OLLAMA_MODEL=${OLLAMA_MODEL}
    - OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH}
    - GDRIVE_SYNC_PATH=${GDRIVE_SYNC_PATH}
    - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
    - GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS}
    - GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}
    - LOG_LEVEL=${LOG_LEVEL}
  volumes:
    - ../backend:/app
    - ${LOCAL_OBSIDIAN_PATH:-../data/vault}:/app/data/vault:ro
    - ${GOOGLE_APPLICATION_CREDENTIALS:-../credentials}:/app/credentials:ro
  ports:
    - "8000:8000"
  depends_on:
    postgres:
      condition: service_healthy
  extra_hosts:
    - "host.docker.internal:host-gateway"
  networks:
    - maestro-network
  command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Ollama (Host-based, NOT in Docker)
- **Installation**: Runs directly on host system
- **Port**: 11434 (accessed via `host.docker.internal`)
- **Purpose**: Local LLM inference
- **Why Not Containerized**:
  - Better GPU access
  - Easier model management
  - Shared with other local applications
  - Avoids port conflicts

**Backend Access Configuration**:
- Windows/Mac Docker Desktop: `http://host.docker.internal:11434`
- Linux (with host networking): `http://localhost:11434`

#### 4. Frontend (Optional, Multiple Options)
Maestro provides several frontend options, none running by default:

**Option A: Maestro UI**
- **Location**: `maestro-ui/` directory
- **Technology**: React + TypeScript + Vite
- **Ports**: 3000 (dev) or 80 (production via Nginx)
- **Deployment**: Separate from docker-compose (npm run dev)

**Option B: Open WebUI**
- **Status**: Disabled by default in docker-compose.yml
- **Reason**: GitHub Container Registry access issues
- **Setup**: Manual (see `docs/guides/openwebui-setup.md`)
- **Port**: 3000 (if enabled)

**Option C: Direct API**
- No frontend needed
- Access API at http://localhost:8000/docs

## Networking Architecture

### Docker Network Configuration

All Docker services connect to a custom bridge network:

```yaml
networks:
  maestro-network:
    driver: bridge
```

**Benefits of Bridge Network**:
- Service isolation
- Automatic DNS resolution (services can reach each other by name)
- Better security than host networking
- Compatible with external host services via `host.docker.internal`

### Host Integration

#### `host.docker.internal` Bridge

The backend service uses `extra_hosts` to connect to host services:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This allows the backend to access:
- Ollama on the host system
- Any other host-based services
- Host filesystem (via volume mounts)

**Platform Differences**:
- **Windows/Mac Docker Desktop**: `host.docker.internal` is built-in
- **Linux**: Added via `host-gateway` in extra_hosts

### Port Mappings

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Backend | 8000 | 8000 | API endpoints, docs |
| PostgreSQL | 5432 | 5432 | Database (for debugging) |
| Ollama (Host) | 11434 | 11434 | LLM inference |
| Maestro UI (Optional) | 3000 | 3000 | Web interface (dev) |
| Maestro UI (Prod) | 80 | 80 | Web interface (nginx) |

## Volume Management

### Persistent Volumes

```yaml
volumes:
  postgres_data:  # PostgreSQL database files
  # ollama_data: (disabled - using host Ollama)
  # openwebui_data: (disabled - Open WebUI optional)
```

**Active Volumes**:
- `postgres_data`: Persists database across container restarts

**Volume Locations**:
```bash
# List volumes
docker volume ls | grep infra

# Inspect volume
docker volume inspect infra_postgres_data

# Backup volume
docker run --rm -v infra_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data
```

### Bind Mounts

| Source (Host) | Target (Container) | Mode | Purpose |
|---------------|-------------------|------|---------|
| `../backend` | `/app` | rw | Hot-reload development |
| `${LOCAL_OBSIDIAN_PATH}` | `/app/data/vault` | ro | Read Obsidian vault |
| `${GOOGLE_APPLICATION_CREDENTIALS}` | `/app/credentials` | ro | Google Cloud credentials |

**Read-Only Mounts**:
- Obsidian vault: Prevents accidental modifications
- Credentials: Security best practice

## Service Dependencies

### Dependency Graph

```
┌──────────────┐
│  PostgreSQL  │
└──────┬───────┘
       │
       │ (waits for healthy)
       │
┌──────▼───────┐     ┌────────────────┐
│   Backend    ├────►│ Ollama (Host)  │
└──────────────┘     └────────────────┘
                      (via host.docker.internal)
```

### Startup Sequence

1. **PostgreSQL** starts first
2. PostgreSQL healthcheck runs (every 10 seconds, up to 5 retries)
3. Once PostgreSQL is healthy, **Backend** starts
4. Backend connects to:
   - PostgreSQL (via Docker network)
   - Ollama (via host.docker.internal)
5. Backend healthcheck confirms successful startup

### Healthchecks

**PostgreSQL**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Backend**:
```yaml
healthcheck:
  --interval=30s
  --timeout=10s
  --start-period=40s
  --retries=3
CMD curl -f http://localhost:8000/health || exit 1
```

## Deployment Procedures

### Initial Deployment

```bash
# 1. Clone repository
git clone https://github.com/lordmuffin/Maestro.git
cd Maestro

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Run setup script (creates directories, starts services)
./scripts/setup/first_run.sh  # Linux/Mac
# OR
powershell -ExecutionPolicy Bypass -File .\scripts\setup\first_run.ps1  # Windows

# 4. Verify deployment
docker ps  # Check running containers
curl http://localhost:8000/health  # Check backend
```

### Updating Deployment

```bash
# Pull latest changes
git pull origin main

# Rebuild backend (if Dockerfile or dependencies changed)
cd infra
docker compose build backend

# Restart services
docker compose down
docker compose up -d

# Check logs
docker compose logs -f
```

### Stopping Services

```bash
cd infra

# Stop all services (keeps data)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop, remove containers, and delete volumes (DESTRUCTIVE)
docker compose down -v
```

### Viewing Logs

```bash
cd infra

# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres

# Last 100 lines
docker compose logs --tail=100 backend
```

## Configuration Files

### docker-compose.yml Location

**Important**: All docker-compose commands must be run from the `infra/` directory:

```bash
cd infra
docker compose up -d  # ✅ Correct

# NOT from root directory:
docker compose up -d  # ❌ Wrong - will fail
```

### Environment Variables

Environment variables are loaded from `.env` file:
- **Root directory**: `Maestro/.env` (main configuration)
- **Symlink**: `Maestro/infra/.env` → `../env` (for docker-compose)

**Required Variables**:
```bash
# Database
POSTGRES_USER=maestro
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=maestro
DATABASE_URL=postgresql://maestro:secure_password@postgres:5432/maestro

# Ollama
OLLAMA_HOST=http://host.docker.internal:11434  # Windows/Mac
# OLLAMA_HOST=http://localhost:11434  # Linux
OLLAMA_MODEL=llama3:8b

# Backend
LOG_LEVEL=INFO

# Obsidian
LOCAL_OBSIDIAN_PATH=/path/to/vault
```

## Security Considerations

### Network Security

- **Bridge Network**: Provides isolation from host network
- **Internal Communication**: Services communicate within Docker network
- **Exposed Ports**: Only necessary ports are exposed to host
  - 8000: Backend API (required)
  - 5432: PostgreSQL (debugging only - can be removed)

### Secrets Management

- **Environment Variables**: Stored in `.env` (gitignored)
- **Credentials Files**: Placed in `credentials/` (gitignored)
- **Database Password**: Should be strong and unique
- **Volume Permissions**: Read-only mounts for sensitive data

### Production Recommendations

1. **Change Default Passwords**: Use strong, unique passwords for PostgreSQL
2. **Restrict PostgreSQL Port**: Remove 5432 port mapping in production
3. **Use HTTPS**: Set up reverse proxy (Nginx/Traefik) with TLS
4. **Volume Backups**: Regular backups of `postgres_data` volume
5. **Firewall Rules**: Restrict access to necessary ports only
6. **Update Images**: Keep base images updated (`docker compose pull`)

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check all container health
docker ps

# Query backend health endpoint
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
docker volume ls
```

### Database Maintenance

```bash
# Connect to PostgreSQL
docker exec -it maestro-postgres psql -U maestro -d maestro

# Backup database
docker exec maestro-postgres pg_dump -U maestro maestro > backup.sql

# Restore database
docker exec -i maestro-postgres psql -U maestro maestro < backup.sql
```

## Troubleshooting Deployment

### Service Won't Start

```bash
# Check container logs
docker logs maestro-backend
docker logs maestro-postgres

# Inspect container
docker inspect maestro-backend

# Check network
docker network inspect infra_maestro-network
```

### Port Conflicts

```bash
# Find process using port
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# Kill process or change port in .env
```

### Volume Issues

```bash
# List volumes
docker volume ls

# Remove unused volumes
docker volume prune

# Inspect volume
docker volume inspect infra_postgres_data
```

## Scaling Considerations

While Maestro currently uses docker-compose, future scaling options:

### Horizontal Scaling
- **Current**: Single backend instance
- **Future**: Multiple backend replicas behind load balancer
- **Consideration**: Stateless backend design supports scaling

### Database Scaling
- **Current**: Single PostgreSQL instance
- **Future**: PostgreSQL replication, read replicas
- **Consideration**: Connection pooling (PgBouncer)

### Migration to Kubernetes (Future)
If needed, docker-compose configuration can be converted to Kubernetes:
- Services → Deployments
- Volumes → PersistentVolumeClaims
- Networks → Services + NetworkPolicies
- Healthchecks → Liveness/Readiness probes

## References

- Docker Compose Documentation: https://docs.docker.com/compose/
- Docker Networking: https://docs.docker.com/network/
- Docker Volumes: https://docs.docker.com/storage/volumes/
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/docker/
- PostgreSQL Docker: https://hub.docker.com/_/postgres
