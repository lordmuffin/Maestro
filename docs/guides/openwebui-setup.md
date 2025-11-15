# Open WebUI Setup Guide

## Overview

Open WebUI is disabled by default in Maestro due to GitHub Container Registry (ghcr.io) access limitations. This guide explains how to manually enable Open WebUI if you prefer it over Maestro UI or direct API access.

## Why is Open WebUI Disabled?

The official Open WebUI Docker image is hosted on GitHub Container Registry (ghcr.io) which sometimes requires authentication or experiences access issues. To ensure a smooth out-of-the-box experience, we've disabled it by default and provided alternative frontends.

## Prerequisites

Before enabling Open WebUI:
- Maestro backend must be running successfully (`docker ps` shows `maestro-backend` as healthy)
- PostgreSQL must be running
- You must have completed the initial setup (run `first_run.sh` or `first_run.ps1`)

## Option 1: Using Official GitHub Container Registry Image

### Step 1: Authenticate with GitHub Container Registry (if needed)

Some users may need to authenticate:

```bash
# Create a GitHub Personal Access Token with read:packages scope
# Visit: https://github.com/settings/tokens

# Login to ghcr.io
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### Step 2: Pull the Image Manually

```bash
docker pull ghcr.io/open-webui/open-webui:latest
```

If this succeeds, proceed to Step 3. If it fails with "denied: denied", try Option 2 below.

### Step 3: Uncomment Open WebUI in docker-compose.yml

Edit `infra/docker-compose.yml`:

```yaml
  openwebui:
    image: ghcr.io/open-webui/open-webui:latest
    container_name: maestro-webui
    environment:
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - OLLAMA_BASE_URL=${OLLAMA_HOST}
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - ENABLE_SIGNUP=true
      - WEBUI_NAME=Maestro AI Assistant
    volumes:
      - openwebui_data:/app/backend/data
      - ../frontend/open-webui-customizations:/app/backend/data/customizations
    ports:
      - "${WEBUI_PORT}:8080"
    depends_on:
      - postgres
      - backend
    networks:
      - maestro-network
    restart: unless-stopped
```

Also uncomment the volume at the bottom:

```yaml
volumes:
  postgres_data:
  # ollama_data:  # Disabled - using host's Ollama
  openwebui_data:  # Uncomment this line
```

### Step 4: Configure Environment Variables

Ensure your `.env` file has:

```bash
WEBUI_SECRET_KEY=your_random_secret_key_here
WEBUI_PORT=3000
```

Generate a secure secret key:
```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
-join (1..32 | ForEach-Object { '{0:X2}' -f (Get-Random -Maximum 256) })
```

### Step 5: Start Open WebUI

```bash
cd infra
docker compose up -d openwebui
```

### Step 6: Access Open WebUI

Open your browser to: http://localhost:3000

## Option 2: Using Alternative Docker Hub Mirrors

If ghcr.io access continues to fail, some community members maintain mirrors:

⚠️ **Warning**: Use third-party mirrors at your own risk. Always verify the image source.

```bash
# Example using a hypothetical mirror (verify before use)
# Edit docker-compose.yml to use alternative image
image: alternative-registry/open-webui:latest
```

## Option 3: Build from Source

For maximum control and security:

### Step 1: Clone Open WebUI Repository

```bash
cd /tmp
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

### Step 2: Build the Image

```bash
docker build -t local/open-webui:latest .
```

### Step 3: Update docker-compose.yml

Change the image line:

```yaml
openwebui:
  image: local/open-webui:latest
  # ... rest of configuration
```

### Step 4: Start the Service

```bash
cd /path/to/maestro/infra
docker compose up -d openwebui
```

## Verification

After enabling Open WebUI:

1. **Check Container Status**:
   ```bash
   docker ps | grep maestro-webui
   # Should show "Up" status
   ```

2. **Check Logs**:
   ```bash
   docker logs maestro-webui
   # Should show successful startup messages
   ```

3. **Access Web Interface**:
   - Navigate to http://localhost:3000
   - You should see the Open WebUI login/signup page

4. **Create Initial Account**:
   - First user to sign up becomes admin
   - Use a secure password

## Troubleshooting

### Issue: Image Pull Fails with "denied: denied"

**Solution**: GitHub Container Registry requires authentication. Either:
- Try Option 1 with authentication
- Use Option 3 (build from source)
- Use Maestro UI instead (no registry issues)

### Issue: Container Starts but Port 3000 Not Accessible

**Solutions**:
- Check if another service is using port 3000: `netstat -ano | grep 3000` (Windows) or `lsof -i :3000` (Linux/Mac)
- Change WEBUI_PORT in `.env` to different port (e.g., 3001)
- Verify firewall settings

### Issue: Open WebUI Shows "Database Connection Error"

**Solutions**:
- Verify PostgreSQL is running: `docker ps | grep postgres`
- Check DATABASE_URL in Open WebUI environment matches your `.env` settings
- Ensure POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB are set correctly
- Wait for PostgreSQL healthcheck (takes ~15 seconds)

### Issue: Open WebUI Cannot Connect to Backend

**Solutions**:
- Verify backend is healthy: `curl http://localhost:8000/health`
- Check Docker network: All services should be on `maestro-network`
- Review Open WebUI logs: `docker logs maestro-webui`

### Issue: Ollama Integration Not Working in Open WebUI

**Solutions**:
- Open WebUI needs to access Ollama via OLLAMA_BASE_URL
- Should be set to `${OLLAMA_HOST}` which points to `http://host.docker.internal:11434`
- Verify Ollama is running on host: `ollama list`
- Test Ollama access from backend: `docker exec maestro-backend curl http://host.docker.internal:11434/api/tags`

## Reverting to Disabled State

If you want to disable Open WebUI again:

```bash
cd infra
docker compose stop openwebui
docker compose rm openwebui

# Optionally remove the volume (deletes Open WebUI data)
docker volume rm infra_openwebui_data
```

Then re-comment the service in `docker-compose.yml`.

## Alternative: Use Maestro UI

If Open WebUI setup is problematic, consider using Maestro UI instead:

```bash
cd maestro-ui
npm install
npm run dev
```

See `maestro-ui/README.md` for full instructions.

## Getting Help

If you continue to experience issues:
1. Check the main troubleshooting guide: `docs/troubleshooting.md`
2. Review Open WebUI documentation: https://docs.openwebui.com
3. Report Maestro-specific issues: https://github.com/lordmuffin/Maestro/issues
4. For Open WebUI issues: https://github.com/open-webui/open-webui/issues

## Security Considerations

- Always use a strong WEBUI_SECRET_KEY
- The first user to sign up becomes admin - secure this account immediately
- Consider disabling signup after creating admin: Set `ENABLE_SIGNUP=false` in docker-compose.yml
- Open WebUI stores data in a Docker volume - back up `openwebui_data` volume regularly
- If exposing to network, use HTTPS and proper authentication

## References

- Open WebUI GitHub: https://github.com/open-webui/open-webui
- Open WebUI Documentation: https://docs.openwebui.com
- GitHub Container Registry: https://ghcr.io
- Docker Hub: https://hub.docker.com
