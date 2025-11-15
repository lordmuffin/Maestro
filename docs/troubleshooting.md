# Maestro Troubleshooting Guide

Comprehensive troubleshooting for Maestro setup, deployment, and runtime issues.

## Table of Contents

1. [Setup Issues](#setup-issues)
2. [Docker and Container Issues](#docker-and-container-issues)
3. [Network and Connectivity](#network-and-connectivity)
4. [Database Issues](#database-issues)
5. [Ollama Integration](#ollama-integration)
6. [Frontend Issues](#frontend-issues)
7. [Performance Issues](#performance-issues)
8. [Data and Storage](#data-and-storage)

---

## Setup Issues

### PowerShell Script Errors (Windows)

#### Symptom
```
Unexpected token '}' in expression or statement.
```

#### Cause
- Script contains curly quotes (`''` or `""`) instead of straight quotes
- Incorrect file encoding (UTF-8 with BOM or wrong line endings)

#### Solutions

**Option 1: Fix Encoding**
```powershell
# Re-download scripts or fix encoding
# Ensure UTF-8 without BOM, CRLF line endings
```

**Option 2: Use WSL**
```bash
# If you have Windows Subsystem for Linux
wsl
bash ./scripts/setup/first_run.sh
```

**Option 3: Use Git Bash**
```bash
# If you have Git for Windows
bash ./scripts/setup/first_run.sh
```

**Option 4: Manual Cleanup**
```powershell
# Replace curly quotes with straight quotes in text editor
# Visual Studio Code: Search for [''] and replace with [']
```

### `.env` Configuration Errors

#### Symptom
- Services start but don't connect to each other
- Environment variables not loaded

#### Solutions

**Check .env Location**
```bash
# .env should be in root directory
ls -la .env

# Symlink should exist in infra/ directory
ls -la infra/.env
```

**Verify .env Format**
```bash
# No spaces around =
POSTGRES_USER=maestro  # ✅ Correct
POSTGRES_USER = maestro  # ❌ Wrong

# Use straight quotes, not curly
OLLAMA_HOST="http://host.docker.internal:11434"  # ✅ Correct
```

**Required vs Optional Variables**
```bash
# Required (must be set)
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
DATABASE_URL
OLLAMA_HOST
OLLAMA_MODEL

# Optional (for Phase 2 features)
GOOGLE_CLOUD_PROJECT
GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_DRIVE_FOLDER_ID

# Optional (if using Open WebUI)
WEBUI_SECRET_KEY
WEBUI_PORT
```

### Setup Script Fails Midway

#### Symptom
- Script starts but exits with error
- Containers partially created

#### Diagnosis
```bash
# Check what's running
docker ps -a

# Check logs
cd infra
docker compose logs
```

#### Solutions

**Clean Up and Retry**
```bash
cd infra
docker compose down
docker compose down -v  # If you want to reset database

# Fix any issues in .env
nano ../.env  # or vim, notepad, etc.

# Retry setup
cd ..
./scripts/setup/first_run.sh
```

**Check Disk Space**
```bash
# Ensure adequate disk space (20GB+ recommended)
df -h  # Linux/Mac
Get-PSDrive  # Windows PowerShell
```

---

## Docker and Container Issues

### Docker Compose Not Found

#### Symptom
```
docker-compose: command not found
# OR
docker: 'compose' is not a docker command
```

#### Solutions

**Check Docker Installation**
```bash
docker --version
```

**Install Docker Compose**
```bash
# Docker Desktop (Windows/Mac) - includes Compose V2
# Download from: https://www.docker.com/products/docker-desktop/

# Linux - Install Compose V2
sudo apt-get update
sudo apt-get install docker-compose-plugin

# OR use legacy V1
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Container Fails to Start

#### Symptom
- Container exits immediately after starting
- Shows "Exited (1)" or similar status

#### Diagnosis
```bash
# Check container status
docker ps -a | grep maestro

# View logs
docker logs maestro-backend
docker logs maestro-postgres

# Inspect container
docker inspect maestro-backend
```

#### Common Causes

**Port Already in Use**
```bash
# Check what's using the port
# Windows
netstat -ano | findstr :8000
tasklist | findstr <PID>

# Linux/Mac
lsof -i :8000
ps aux | grep <PID>

# Solution: Stop conflicting service or change port in .env
BACKEND_PORT=8001  # Change port
```

**Missing Dependencies**
```bash
# Backend missing Python packages
cd infra
docker compose build --no-cache backend
docker compose up -d backend
```

**Database Not Ready**
```bash
# Backend started before PostgreSQL was healthy
# Solution: Wait and restart
docker compose restart backend

# Check PostgreSQL health
docker ps | grep postgres
# Should show "(healthy)" after ~15 seconds
```

### `host.docker.internal` Not Resolving

#### Symptom
```
ERROR: Cannot connect to host.docker.internal:11434
```

#### Platform-Specific Solutions

**Windows/Mac Docker Desktop**
```bash
# Should work out of the box
# Ensure .env has:
OLLAMA_HOST=http://host.docker.internal:11434

# Test from container
docker exec maestro-backend ping host.docker.internal
```

**Linux**
```bash
# Option 1: Use localhost with host networking
# Edit infra/docker-compose.yml:
network_mode: "host"  # Add to backend service
# Set in .env:
OLLAMA_HOST=http://localhost:11434

# Option 2: Use host IP address
# Find host IP
ip addr show docker0 | grep inet

# Set in .env:
OLLAMA_HOST=http://172.17.0.1:11434  # Use your docker0 IP
```

**Verify Connection**
```bash
# From backend container
docker exec maestro-backend curl http://host.docker.internal:11434/api/tags

# Should return list of Ollama models
```

---

## Network and Connectivity

### Backend API Not Accessible

#### Symptom
- Cannot access http://localhost:8000/docs
- Connection refused errors

#### Diagnosis
```bash
# Check backend container
docker ps | grep backend

# Check if port is actually exposed
docker port maestro-backend

# Check backend logs
docker logs maestro-backend
```

#### Solutions

**Firewall Blocking Port**
```bash
# Windows - Allow port through firewall
New-NetFirewallRule -DisplayName "Maestro Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Linux - ufw
sudo ufw allow 8000/tcp

# Linux - firewalld
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

**Docker Not Exposing Port**
```bash
# Verify docker-compose.yml has ports section:
ports:
  - "8000:8000"

# Restart services
cd infra
docker compose down
docker compose up -d
```

**Backend Application Error**
```bash
# Check Python application logs
docker logs maestro-backend --tail 50

# Common issues:
# - Import errors (missing dependencies)
# - Database connection failed
# - Configuration errors
```

### Cannot Connect Between Containers

#### Symptom
- Backend cannot reach PostgreSQL
- Services on same Docker network but not communicating

#### Diagnosis
```bash
# Check Docker network
docker network ls | grep maestro
docker network inspect infra_maestro-network

# Verify all containers are on same network
```

#### Solutions

**Recreate Network**
```bash
cd infra
docker compose down
docker network prune
docker compose up -d
```

**Check Service Names**
```bash
# Services communicate using container names
# Backend should use: postgres (not localhost or 127.0.0.1)
# Correct DATABASE_URL:
DATABASE_URL=postgresql://user:pass@postgres:5432/maestro

# NOT:
DATABASE_URL=postgresql://user:pass@localhost:5432/maestro  # Wrong
```

---

## Database Issues

### PostgreSQL Won't Start

#### Symptom
```
maestro-postgres exited with code 1
```

#### Diagnosis
```bash
docker logs maestro-postgres
```

#### Common Causes

**Permission Errors**
```
initdb: error: could not change permissions of directory "/var/lib/postgresql/data"
```

**Solution**:
```bash
# Remove volume and recreate
cd infra
docker compose down -v
docker volume rm infra_postgres_data
docker compose up -d
```

**Port Conflict**
```bash
# Port 5432 already in use
# Find conflicting service
# Windows
netstat -ano | findstr :5432

# Linux/Mac
lsof -i :5432

# Solution: Stop PostgreSQL on host or change port
ports:
  - "5433:5432"  # Change external port
```

### Database Connection Refused

#### Symptom
```
connection to server at "postgres" (172.18.0.2), port 5432 failed: Connection refused
```

#### Solutions

**Wait for Healthcheck**
```bash
# PostgreSQL needs ~10-15 seconds to become healthy
docker ps | grep postgres
# Wait until you see "(healthy)"

# Then restart backend
docker compose restart backend
```

**Check Database Credentials**
```bash
# Verify .env matches docker-compose.yml
# All these must match:
POSTGRES_USER=maestro
POSTGRES_PASSWORD=your_password
POSTGRES_DB=maestro
DATABASE_URL=postgresql://maestro:your_password@postgres:5432/maestro
```

**Test Database Access**
```bash
# Connect to database from host
docker exec -it maestro-postgres psql -U maestro -d maestro

# If successful, you'll see:
maestro=#
```

### Database Migration Errors

#### Symptom
- Backend starts but API calls fail
- Errors about missing tables or columns

#### Solutions

**Run Migrations**
```bash
# Access backend container
docker exec -it maestro-backend bash

# Run Alembic migrations
alembic upgrade head

# Exit container
exit
```

**Reset Database (DESTRUCTIVE)**
```bash
cd infra
docker compose down
docker volume rm infra_postgres_data
docker compose up -d

# Wait for PostgreSQL healthy, then restart backend
docker compose restart backend
```

---

## Ollama Integration

### Ollama Not Running

#### Symptom
```
Failed to connect to Ollama: Connection refused
```

#### Solutions

**Start Ollama Service**
```bash
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve &  # Linux/Mac background
# OR
ollama serve  # Windows (keep terminal open)
```

**Install Ollama**
```bash
# If not installed
# Visit: https://ollama.com/download
# Or use package manager:

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Mac
brew install ollama

# Windows
# Download installer from ollama.com
```

**Verify Ollama is Accessible**
```bash
# From host
curl http://localhost:11434/api/tags

# Should return JSON with model list
```

### Ollama Models Not Found

#### Symptom
```
Error: model 'llama3:8b' not found
```

#### Solutions

**Pull Required Model**
```bash
# Pull the model specified in .env
ollama pull llama3:8b

# Or pull a different model and update .env
ollama pull llama3.1:8b
# Then update .env:
OLLAMA_MODEL=llama3.1:8b
```

**List Available Models**
```bash
ollama list
```

**Check Model Compatibility**
```bash
# Ensure adequate RAM
# llama3:8b requires ~8GB RAM
# llama3:70b requires ~48GB RAM

# Check system RAM
free -h  # Linux
vm_stat  # Mac
systeminfo | findstr Memory  # Windows
```

### Backend Cannot Reach Ollama

#### Symptom
```
Error connecting to Ollama at http://host.docker.internal:11434
```

#### Solutions

**Verify Ollama is Listening**
```bash
# Ollama should listen on all interfaces
ollama serve --host 0.0.0.0

# Or check if it's already listening
# Linux/Mac
netstat -an | grep 11434

# Windows
netstat -an | findstr 11434
```

**Test from Backend Container**
```bash
docker exec maestro-backend curl http://host.docker.internal:11434/api/tags

# If this fails, networking issue
# If this succeeds, application configuration issue
```

**Check OLLAMA_HOST Configuration**
```bash
# Windows/Mac Docker Desktop
OLLAMA_HOST=http://host.docker.internal:11434

# Linux (varies by setup)
OLLAMA_HOST=http://localhost:11434  # With host networking
# OR
OLLAMA_HOST=http://172.17.0.1:11434  # Docker bridge network
```

---

## Frontend Issues

### Port 3000 Not Accessible

#### Symptom
- Cannot access http://localhost:3000
- Connection refused

#### Cause
Open WebUI is disabled by default.

#### Solutions

**Option 1: Use Maestro UI**
```bash
cd maestro-ui
npm install
npm run dev
# Access at http://localhost:3000
```

**Option 2: Use Direct API**
```bash
# No frontend needed
# Access API at http://localhost:8000/docs
```

**Option 3: Enable Open WebUI**
```bash
# See: docs/guides/openwebui-setup.md
# Requires manual setup
```

### Maestro UI Won't Start

#### Symptom
```
npm run dev fails
Module not found errors
```

#### Solutions

**Install Dependencies**
```bash
cd maestro-ui
rm -rf node_modules package-lock.json
npm install
```

**Check Node Version**
```bash
node --version  # Should be 18.x or higher
npm --version   # Should be 9.x or higher

# Update if needed:
# Visit: https://nodejs.org/
```

**Port Conflict**
```bash
# If port 3000 is in use
# Edit maestro-ui/vite.config.ts or package.json
# Change port to 3001 or another free port
```

### Open WebUI Enabled But Not Working

#### Symptom
- Open WebUI container running but can't access it
- Shows login but errors on signup

#### Solutions

**Check Container Logs**
```bash
docker logs maestro-webui

# Look for:
# - Database connection errors
# - Port binding issues
# - Configuration errors
```

**Verify Environment Variables**
```bash
# Must have in .env:
WEBUI_SECRET_KEY=<your-secret-key>
WEBUI_PORT=3000
POSTGRES_USER=maestro
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=maestro
```

**Database Connection**
```bash
# Open WebUI needs PostgreSQL
# Verify DATABASE_URL in docker-compose.yml:
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

---

## Performance Issues

### Slow API Response Times

#### Causes
- Large Obsidian vault (indexing)
- Ollama model too large for available RAM
- Database queries not optimized

#### Solutions

**Check Resource Usage**
```bash
# Container stats
docker stats

# System resources
htop  # Linux/Mac
Task Manager  # Windows
```

**Optimize Ollama Model**
```bash
# Use smaller model for better performance
ollama pull llama3:8b  # Fast, 8GB RAM
# Instead of:
ollama pull llama3:70b  # Slow, 48GB RAM

# Update .env
OLLAMA_MODEL=llama3:8b
```

**Index Obsidian Vault**
```bash
# Trigger reindexing
curl -X POST http://localhost:8000/api/v1/rag/index
```

### High Memory Usage

#### Solutions

**Limit Docker Resources**
```bash
# Edit Docker Desktop settings
# Resources -> Advanced
# Reduce Memory to required amount + 2GB buffer
```

**Optimize Ollama**
```bash
# Use quantized models (smaller, faster)
ollama pull llama3:8b-q4_0  # 4-bit quantization
```

**Check for Memory Leaks**
```bash
# Restart containers periodically
cd infra
docker compose restart backend
```

---

## Data and Storage

### Obsidian Vault Not Found

#### Symptom
```
Error: Vault directory does not exist: /app/data/vault
```

#### Solutions

**Verify Path in .env**
```bash
# Windows - Use forward slashes
LOCAL_OBSIDIAN_PATH=C:/Users/yourname/Documents/ObsidianVault

# Linux/Mac - Absolute path
LOCAL_OBSIDIAN_PATH=/home/yourname/Documents/ObsidianVault

# Check directory exists
ls "${LOCAL_OBSIDIAN_PATH}"
```

**Check Volume Mount**
```bash
# Inspect backend container
docker inspect maestro-backend | grep -A 10 Mounts

# Should show vault mounted to /app/data/vault
```

**Permissions**
```bash
# Ensure vault is readable
chmod -R 755 /path/to/vault  # Linux/Mac

# Windows - Right-click folder -> Properties -> Security
# Ensure your user has Read permissions
```

### Database Data Lost After Restart

#### Cause
Volume not persisting or using wrong volume.

#### Solutions

**Check Volume Exists**
```bash
docker volume ls | grep postgres
# Should see: infra_postgres_data
```

**Verify Volume Mount**
```bash
docker inspect maestro-postgres | grep -A 5 Mounts
# Should show volume mounted to /var/lib/postgresql/data
```

**Don't Use `-v` Flag**
```bash
# WRONG - deletes volumes
docker compose down -v

# CORRECT - keeps volumes
docker compose down
```

### Disk Space Errors

#### Symptom
```
no space left on device
```

#### Solutions

**Check Disk Usage**
```bash
df -h  # Linux/Mac
Get-PSDrive  # Windows

# Docker-specific
docker system df
```

**Clean Up Docker**
```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes (CAREFUL - may delete data)
docker volume prune

# Clean build cache
docker builder prune
```

**Free Up Space**
```bash
# Remove old Ollama models
ollama list
ollama rm <model-name>

# Clean system cache (OS-specific)
```

---

## Getting Additional Help

If issues persist after trying these solutions:

### 1. Gather Diagnostic Information

```bash
# System info
uname -a  # Linux/Mac
systeminfo  # Windows

# Docker info
docker --version
docker compose version
docker info

# Container status
docker ps -a

# Service logs
cd infra
docker compose logs > maestro-logs.txt

# Health check
curl http://localhost:8000/health
```

### 2. Check Documentation

- Main README: `README.md`
- Deployment Architecture: `docs/deployment-architecture.md`
- Open WebUI Setup: `docs/guides/openwebui-setup.md`
- Phase 2 Guide: `docs/guides/phase2-cloud-integration.md`

### 3. Search Existing Issues

- Maestro Issues: https://github.com/lordmuffin/Maestro/issues
- Open WebUI Issues: https://github.com/open-webui/open-webui/issues
- Ollama Issues: https://github.com/ollama/ollama/issues

### 4. Report New Issue

Include in your issue report:
- Operating system and version
- Docker and Docker Compose versions
- Relevant log files
- Steps to reproduce
- Expected vs actual behavior
- Configuration files (.env with secrets redacted)

**GitHub**: https://github.com/lordmuffin/Maestro/issues

### 5. Community Support

- Discussions: https://github.com/lordmuffin/Maestro/discussions
- Check README for communication channels

---

## Quick Reference Commands

```bash
# Status checks
docker ps                                    # Container status
docker compose logs -f                       # Follow logs
curl http://localhost:8000/health            # Backend health
ollama list                                  # Ollama models

# Restarts
docker compose restart backend               # Restart backend
docker compose restart                       # Restart all

# Clean start
docker compose down                          # Stop
docker compose up -d                         # Start

# Nuclear option (resets everything)
docker compose down -v                       # Delete volumes too
docker system prune -a                       # Clean Docker
# Then run setup script again

# Debugging
docker exec -it maestro-backend bash         # Enter backend
docker exec -it maestro-postgres psql -U maestro -d maestro  # Enter database
docker logs --tail 50 maestro-backend        # Last 50 log lines
```
