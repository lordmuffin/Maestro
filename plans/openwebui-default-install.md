# Implementation Plan: Open WebUI Default Installation

## Document Information

- **Created**: 2025-01-11
- **Status**: Proposal
- **Priority**: Medium
- **Target Completion**: 17 days from approval
- **Owner**: TBD
- **Reviewers**: Project maintainers

## Executive Summary

This document outlines a comprehensive plan to make Open WebUI install and run by default in Maestro, replacing the current manual setup process. The plan addresses the root cause of GitHub Container Registry (GHCR) authentication issues by implementing a hybrid fallback approach that tries the official GHCR image first, then automatically falls back to verified Docker Hub mirrors if access is denied.

**Key Goals**:
- Enable Open WebUI by default for all new Maestro installations
- Implement automatic fallback mechanism for image source
- Maintain user privacy and security standards
- Provide opt-out capability for users who prefer API-only or alternative frontends

**Estimated Timeline**: 17 days
**Risk Level**: Medium (primary risk: Docker Hub mirror trustworthiness verification)

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Root Cause Analysis](#2-root-cause-analysis)
3. [Alternative Solutions Evaluated](#3-alternative-solutions-evaluated)
4. [Recommended Approach](#4-recommended-approach)
5. [Detailed Implementation Requirements](#5-detailed-implementation-requirements)
6. [Risks and Mitigation](#6-risks-and-mitigation)
7. [Testing Requirements](#7-testing-requirements)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Decision Summary](#9-decision-summary)
10. [Open Items and Blockers](#10-open-items-and-blockers)
11. [Appendices](#11-appendices)

---

## 1. Current State Analysis

### 1.1 Current Deployment Architecture

Maestro currently uses **docker-compose** for orchestration with the following services:

```yaml
services:
  postgres:       # PostgreSQL 16 - Port 5432
  backend:        # FastAPI Backend - Port 8000
  # open-webui:   # DISABLED - Manual setup required
  # ollama:       # DISABLED - Runs on host instead
```

**Open WebUI Status**:
- Commented out in `infra/docker-compose.yml` (lines 78-100)
- Manual setup documented in `docs/guides/openwebui-setup.md`
- Requires GHCR authentication or alternative image source

### 1.2 Current User Experience

**Setup Flow**:
1. User runs `scripts/setup/first_run.sh` or `first_run.ps1`
2. Backend and PostgreSQL start successfully
3. No frontend UI is available
4. User must read documentation to discover Open WebUI exists
5. User must manually enable Open WebUI following 3-option guide
6. User must handle GHCR authentication or find alternative images

**Pain Points**:
- Unexpected: Users expect a web UI to be available immediately
- Friction: Manual setup requires technical knowledge of Docker authentication
- Discovery: Many users may not realize Open WebUI is even an option
- Alternatives confusion: Three different setup paths create decision paralysis

### 1.3 Documentation State

Current documentation structure:
```
docs/
├── guides/
│   ├── openwebui-setup.md          # Manual setup guide (3 options)
│   ├── phase2-cloud-integration.md # Cloud features (optional)
│   └── ...
├── deployment-architecture.md      # Docker compose architecture
├── troubleshooting.md              # General troubleshooting
├── llm-configuration.md            # Ollama/LLM setup
└── phase4_skills_framework.md      # Skills/API reference
```

**Open WebUI References**:
- README.md: Lists as "Optional, Manual Setup Required" (line ~85)
- openwebui-setup.md: 3 different installation methods
- deployment-architecture.md: Notes it's disabled by default
- phase4_skills_framework.md: Shows API alternatives

### 1.4 Current Configuration Files

**docker-compose.yml** (lines 78-100):
```yaml
# open-webui:
#   image: ghcr.io/open-webui/open-webui:latest
#   container_name: maestro-openwebui
#   ports:
#     - "${WEBUI_PORT:-3000}:8080"
#   environment:
#     - OLLAMA_BASE_URL=http://host.docker.internal:11434
#     - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
#   volumes:
#     - openwebui_data:/app/backend/data
#   extra_hosts:
#     - "host.docker.internal:host-gateway"
#   networks:
#     - maestro-network
```

**.env**:
```bash
# Open WebUI (currently disabled)
WEBUI_SECRET_KEY=maestro_secret_key_change_in_production
WEBUI_PORT=3000
```

### 1.5 Identified Gaps

1. **No automatic image fallback**: Setup scripts don't handle GHCR failures
2. **No pre-flight checks**: No validation of image source availability before pull
3. **No opt-out mechanism**: Users who don't want UI must manually comment out service
4. **Inconsistent messaging**: Docs say "optional" but users expect UI by default
5. **No mirror verification**: No process to validate trustworthiness of Docker Hub mirrors

---

## 2. Root Cause Analysis

### 2.1 Why GHCR Access Fails

**Problem**: `docker compose pull` fails with:
```
Error response from daemon: Head "https://ghcr.io/v2/open-webui/open-webui/manifests/latest": denied: denied
```

**Root Causes**:

1. **GHCR Authentication Required**:
   - GitHub Container Registry requires authentication for many public images
   - Public images still return 403/denied without proper auth token
   - Docker daemon doesn't have GitHub credentials configured

2. **No Token in Request**:
   - Docker compose doesn't automatically pass GitHub credentials
   - `docker login ghcr.io` must be done separately before pull
   - Token must be a GitHub Personal Access Token (PAT) with `read:packages` scope

3. **Corporate Firewall/Proxy Issues**:
   - Some networks block ghcr.io entirely
   - Proxy configurations may not pass auth headers correctly
   - Rate limiting on corporate networks

4. **Docker Hub vs GHCR Differences**:
   - Docker Hub: More lenient with anonymous pulls (rate limits but works)
   - GHCR: Stricter authentication requirements
   - Open WebUI chose GHCR for GitHub-native distribution

### 2.2 Why Current Approach Doesn't Work

**Manual Setup Approach**:
- Puts burden on user to understand Docker registries
- Requires user to create GitHub PAT (friction)
- Multiple paths create confusion
- No guidance on which method is best for their situation

**Disabled by Default**:
- Doesn't match user expectations (modern apps have web UIs)
- Reduces Maestro's perceived completeness
- Forces users to read extensive documentation before getting started
- May cause users to abandon setup thinking it's broken

### 2.3 Why Simple "Uncomment" Won't Work

Just uncommenting the Open WebUI service will fail for most users because:

1. GHCR authentication issues persist
2. No fallback mechanism
3. Setup scripts will exit with errors
4. User is left with broken deployment

### 2.4 Similar Issues in Other Projects

**Observed patterns**:
- Many docker-compose projects face GHCR authentication issues
- Common solution: Provide Docker Hub mirrors or multi-registry fallback
- Best practice: Try official source first, fallback to known mirrors
- Alternative: Build from source (but slow)

---

## 3. Alternative Solutions Evaluated

### 3.1 Option A: Automatic GHCR Authentication

**Description**: Automatically authenticate with GHCR during setup using a shared service account or prompting for user's GitHub PAT.

**Pros**:
- Uses official Open WebUI image
- Always up to date
- No trust issues with mirrors

**Cons**:
- Requires users to create GitHub Personal Access Token
- Adds friction to setup process
- Service account tokens can be revoked
- Doesn't solve corporate firewall issues
- Privacy concerns: sharing GitHub credentials

**Verdict**: ❌ **Rejected** - Too much user friction, doesn't solve all access issues

### 3.2 Option B: Docker Hub Official Mirror

**Description**: Use `docker.io/openwebui/open-webui` if it exists.

**Pros**:
- Docker Hub has better anonymous access
- Most users already authenticated with Docker Hub
- No GitHub dependency

**Cons**:
- Open WebUI doesn't maintain official Docker Hub images
- Available mirrors are community-maintained (trust issues)
- May be out of date or abandoned
- Could be malicious

**Verdict**: ⚠️ **Conditional** - Only if we can verify mirror trustworthiness (see Section 10.1)

### 3.3 Option C: Build from Source

**Description**: Build Open WebUI image locally from GitHub source during setup.

**Pros**:
- Always uses official code
- No registry authentication needed
- Full transparency

**Cons**:
- Adds 5-10 minutes to setup time
- Requires build tools and dependencies
- More complex failure modes
- Higher system requirements (build tools)

**Verdict**: ⚠️ **Fallback Option** - Use only if both GHCR and Docker Hub fail

### 3.4 Option D: Hybrid Fallback Approach (RECOMMENDED)

**Description**: Implement automatic fallback chain:
1. Try GHCR official image (may fail for some users)
2. Fallback to verified Docker Hub mirror (if trustworthy)
3. Fallback to local build (if both registries fail)
4. Inform user and provide manual alternatives

**Implementation**:
```bash
try_image_pull() {
  local image=$1
  local fallback=$2

  echo "Attempting to pull $image..."
  if docker pull "$image" 2>/dev/null; then
    echo "✓ Successfully pulled $image"
    return 0
  fi

  if [ -n "$fallback" ]; then
    echo "⚠ Failed to pull $image, trying fallback: $fallback"
    if docker pull "$fallback" 2>/dev/null; then
      echo "✓ Successfully pulled $fallback"
      # Tag fallback with expected name
      docker tag "$fallback" "$image"
      return 0
    fi
  fi

  return 1
}

# Try GHCR first, fallback to Docker Hub
try_image_pull "ghcr.io/open-webui/open-webui:latest" \
               "docker.io/VERIFIED_MIRROR/open-webui:latest"
```

**Pros**:
- Works for most users without intervention
- Falls back gracefully when GHCR fails
- Uses official image when possible
- Provides path forward even if all registries fail

**Cons**:
- Requires verifying Docker Hub mirror trustworthiness
- More complex setup scripts
- Need to maintain fallback list

**Verdict**: ✅ **RECOMMENDED** - Best balance of reliability and user experience

### 3.5 Option E: Alternative Frontend (Maestro UI)

**Description**: Use Maestro's native React UI instead of Open WebUI.

**Status**: Maestro UI exists in `maestro-ui/` directory but:
- Not containerized
- Runs via `npm run dev` (development only)
- No production build in docker-compose
- Less feature-complete than Open WebUI

**Pros**:
- No external dependencies
- Full control over features
- Tight integration with Maestro APIs

**Cons**:
- Not production-ready
- Requires significant development effort
- Duplicates Open WebUI features

**Verdict**: ❌ **Out of Scope** - Long-term roadmap item, not a solution for immediate need

---

## 4. Recommended Approach

### 4.1 Solution: Hybrid Fallback with Opt-Out

**Core Strategy**:
1. **Enable Open WebUI by default** in docker-compose.yml
2. **Implement image pull fallback chain** in setup scripts
3. **Provide opt-out capability** via environment variable
4. **Update documentation** to reflect new default behavior

### 4.2 Implementation Components

#### Component 1: docker-compose.yml Changes
- Uncomment Open WebUI service
- Add conditional logic based on `OPENWEBUI_ENABLED` variable
- Configure for hybrid image source

#### Component 2: Setup Script Enhancement
- Add image pull retry logic with fallbacks
- Implement pre-flight check for image availability
- Provide clear user messaging about which source was used

#### Component 3: Environment Configuration
- Add `OPENWEBUI_ENABLED=true` to .env.example
- Add `OPENWEBUI_IMAGE_SOURCE` for manual override
- Document all Open WebUI environment variables

#### Component 4: Documentation Updates
- Update README.md to show Open WebUI as default
- Restructure openwebui-setup.md as troubleshooting guide
- Update architecture diagrams

### 4.3 User Experience Flow (After Implementation)

```
User runs setup script
  ↓
Script creates .env from template (OPENWEBUI_ENABLED=true)
  ↓
Script tries: docker pull ghcr.io/open-webui/open-webui:latest
  ├─ Success → Continue with GHCR image
  └─ Failure → Try Docker Hub mirror
      ├─ Success → Continue with mirror (tagged as ghcr.io image)
      └─ Failure → Show manual options, continue without UI
  ↓
docker-compose up -d
  ↓
All services start (including open-webui if image pulled)
  ↓
User browses to http://localhost:3000
  ↓
Open WebUI loads successfully
  ↓
User creates account and starts using Maestro
```

**Opt-Out Flow**:
```
User sets OPENWEBUI_ENABLED=false in .env before setup
  ↓
Setup script skips Open WebUI image pull
  ↓
docker-compose up -d skips open-webui service
  ↓
User uses Maestro via API (localhost:8000/docs)
```

### 4.4 Success Criteria

1. **90%+ Success Rate**: 90% of users successfully get Open WebUI running without manual intervention
2. **Clear Messaging**: Users understand which image source was used and why
3. **Opt-Out Works**: Setting `OPENWEBUI_ENABLED=false` cleanly disables Open WebUI
4. **No Regression**: Existing manual setup methods still work
5. **Documentation Accurate**: All docs reflect new default behavior

---

## 5. Detailed Implementation Requirements

### 5.1 File Changes Required

#### 5.1.1 infra/docker-compose.yml

**Changes**:
1. Uncomment Open WebUI service
2. Add conditional logic for enable/disable
3. Add support for custom image source

**Before** (lines 78-100):
```yaml
# open-webui:
#   image: ghcr.io/open-webui/open-webui:latest
#   container_name: maestro-openwebui
#   ports:
#     - "${WEBUI_PORT:-3000}:8080"
#   ...
```

**After**:
```yaml
open-webui:
  image: ${OPENWEBUI_IMAGE:-ghcr.io/open-webui/open-webui:latest}
  container_name: maestro-openwebui
  ports:
    - "${WEBUI_PORT:-3000}:8080"
  environment:
    - OLLAMA_BASE_URL=http://host.docker.internal:11434
    - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
    - WEBUI_NAME=${WEBUI_NAME:-Maestro AI Assistant}
  volumes:
    - openwebui_data:/app/backend/data
  extra_hosts:
    - "host.docker.internal:host-gateway"
  networks:
    - maestro-network
  restart: unless-stopped
  profiles:
    - ${OPENWEBUI_PROFILE:-default}  # Empty = always run, "disabled" = skip
  depends_on:
    backend:
      condition: service_healthy
```

**Key Changes**:
- `${OPENWEBUI_IMAGE:-...}` allows custom image source override
- `profiles` with conditional enables opt-out via `OPENWEBUI_PROFILE=disabled`
- `restart: unless-stopped` ensures UI restarts after system reboot
- `depends_on: backend` ensures backend is ready before UI starts

**Alternative Approach** (if profiles don't work):
```yaml
# In docker-compose.yml - keep as-is but uncommented
# In docker-compose.override.yml (gitignored):
# Users who want to disable can create this file:
services:
  open-webui:
    profiles:
      - disabled
```

#### 5.1.2 .env.example

**Changes**: Add comprehensive Open WebUI configuration section

**Addition**:
```bash
#############################################
# Open WebUI Configuration
#############################################

# Enable/Disable Open WebUI (default: enabled)
# To disable Open WebUI, set OPENWEBUI_PROFILE=disabled
OPENWEBUI_PROFILE=default

# Open WebUI Image Source
# Default: Official GHCR image (may require GitHub authentication)
# Alternative: docker.io/VERIFIED_MIRROR/open-webui:latest
# Override this if setup script fallback doesn't work for you
OPENWEBUI_IMAGE=ghcr.io/open-webui/open-webui:latest

# Open WebUI Port (default: 3000)
WEBUI_PORT=3000

# Secret key for Open WebUI sessions
# IMPORTANT: Change this to a random string in production
# Generate with: openssl rand -hex 32
WEBUI_SECRET_KEY=your-secret-key-change-in-production

# Open WebUI Display Name
WEBUI_NAME=Maestro AI Assistant

# Open WebUI Authentication
# Set to false to disable authentication (NOT recommended for production)
WEBUI_AUTH=true

# Open WebUI Admin Email (first user becomes admin)
# WEBUI_ADMIN_EMAIL=admin@example.com

# Open WebUI Data Directory (inside container)
# Mapped to Docker volume: openwebui_data
WEBUI_DATA_DIR=/app/backend/data

# Open WebUI Log Level (debug, info, warning, error)
WEBUI_LOG_LEVEL=info
```

#### 5.1.3 scripts/setup/first_run.sh

**Changes**: Add image pull logic with fallback chain

**Addition** (after directory creation, before docker compose pull):
```bash
#!/bin/bash
set -e

# ... existing setup code ...

echo ""
echo "===================================="
echo "Pulling Docker Images"
echo "===================================="

# Function to try pulling image with fallback
try_pull_openwebui() {
  local primary_image="ghcr.io/open-webui/open-webui:latest"
  local fallback_image="VERIFIED_MIRROR_TBD/open-webui:latest"  # TODO: Verify mirror
  local build_from_source=false

  # Check if Open WebUI is disabled
  if grep -q "OPENWEBUI_PROFILE=disabled" .env 2>/dev/null; then
    echo "ℹ Open WebUI is disabled (OPENWEBUI_PROFILE=disabled)"
    echo "  Skipping Open WebUI image pull"
    return 0
  fi

  echo ""
  echo "📦 Pulling Open WebUI image..."
  echo "  Attempting: $primary_image"

  # Try primary (GHCR)
  if docker pull "$primary_image" 2>/dev/null; then
    echo "  ✓ Successfully pulled from GitHub Container Registry"
    return 0
  fi

  echo "  ⚠ Failed to pull from GHCR (may require authentication)"
  echo ""
  echo "  Trying fallback: $fallback_image"

  # Try fallback (Docker Hub mirror)
  if docker pull "$fallback_image" 2>/dev/null; then
    echo "  ✓ Successfully pulled from Docker Hub mirror"
    echo "  ℹ Tagging mirror as primary image..."
    docker tag "$fallback_image" "$primary_image"
    return 0
  fi

  echo "  ⚠ Failed to pull from Docker Hub mirror"
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "⚠  WARNING: Could not automatically pull Open WebUI image"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
  echo "Options to resolve:"
  echo ""
  echo "1. Authenticate with GitHub Container Registry:"
  echo "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
  echo "   (Requires GitHub Personal Access Token with 'read:packages')"
  echo ""
  echo "2. Use Docker Hub mirror (if verified):"
  echo "   docker pull $fallback_image"
  echo "   docker tag $fallback_image $primary_image"
  echo ""
  echo "3. Build from source:"
  echo "   git clone https://github.com/open-webui/open-webui.git"
  echo "   cd open-webui"
  echo "   docker build -t $primary_image ."
  echo ""
  echo "4. Disable Open WebUI and use API only:"
  echo "   echo 'OPENWEBUI_PROFILE=disabled' >> .env"
  echo ""
  echo "Maestro will start without Open WebUI. You can add it later."
  echo "See docs/guides/openwebui-setup.md for detailed instructions."
  echo ""

  # Ask user if they want to continue without Open WebUI
  read -p "Continue without Open WebUI? (y/N): " response
  if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "OPENWEBUI_PROFILE=disabled" >> .env
    echo "✓ Disabled Open WebUI, continuing with setup"
    return 0
  else
    echo "Setup cancelled. Please resolve Open WebUI image issue and try again."
    exit 1
  fi
}

# Pull base images
echo "📦 Pulling PostgreSQL..."
docker compose pull postgres

echo "📦 Building Backend..."
docker compose build backend

# Pull Open WebUI with fallback logic
try_pull_openwebui

echo ""
echo "✓ All images ready"

# ... existing docker compose up code ...
```

**Key Features**:
- Tries GHCR first (silent failure)
- Falls back to Docker Hub mirror (silent failure)
- If both fail, provides detailed troubleshooting
- Allows user to continue without UI or cancel setup
- Auto-disables Open WebUI if user chooses to continue

#### 5.1.4 scripts/setup/first_run.ps1

**Changes**: PowerShell equivalent of bash script changes

**Addition**:
```powershell
# ... existing setup code ...

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Pulling Docker Images" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

function Try-Pull-OpenWebUI {
    $primaryImage = "ghcr.io/open-webui/open-webui:latest"
    $fallbackImage = "VERIFIED_MIRROR_TBD/open-webui:latest"  # TODO: Verify mirror

    # Check if Open WebUI is disabled
    if (Select-String -Path ".env" -Pattern "OPENWEBUI_PROFILE=disabled" -Quiet) {
        Write-Host "ℹ Open WebUI is disabled (OPENWEBUI_PROFILE=disabled)" -ForegroundColor Yellow
        Write-Host "  Skipping Open WebUI image pull"
        return $true
    }

    Write-Host ""
    Write-Host "📦 Pulling Open WebUI image..." -ForegroundColor Cyan
    Write-Host "  Attempting: $primaryImage"

    # Try primary (GHCR)
    $ghcrResult = docker pull $primaryImage 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Successfully pulled from GitHub Container Registry" -ForegroundColor Green
        return $true
    }

    Write-Host "  ⚠ Failed to pull from GHCR (may require authentication)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Trying fallback: $fallbackImage"

    # Try fallback (Docker Hub mirror)
    $fallbackResult = docker pull $fallbackImage 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Successfully pulled from Docker Hub mirror" -ForegroundColor Green
        Write-Host "  ℹ Tagging mirror as primary image..."
        docker tag $fallbackImage $primaryImage
        return $true
    }

    Write-Host "  ⚠ Failed to pull from Docker Hub mirror" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "⚠  WARNING: Could not automatically pull Open WebUI image" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "Options to resolve:"
    Write-Host ""
    Write-Host "1. Authenticate with GitHub Container Registry:"
    Write-Host "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
    Write-Host "   (Requires GitHub Personal Access Token with 'read:packages')"
    Write-Host ""
    Write-Host "2. Use Docker Hub mirror (if verified):"
    Write-Host "   docker pull $fallbackImage"
    Write-Host "   docker tag $fallbackImage $primaryImage"
    Write-Host ""
    Write-Host "3. Build from source:"
    Write-Host "   git clone https://github.com/open-webui/open-webui.git"
    Write-Host "   cd open-webui"
    Write-Host "   docker build -t $primaryImage ."
    Write-Host ""
    Write-Host "4. Disable Open WebUI and use API only:"
    Write-Host "   Add 'OPENWEBUI_PROFILE=disabled' to .env"
    Write-Host ""
    Write-Host "Maestro will start without Open WebUI. You can add it later."
    Write-Host "See docs/guides/openwebui-setup.md for detailed instructions."
    Write-Host ""

    # Ask user if they want to continue without Open WebUI
    $response = Read-Host "Continue without Open WebUI? (y/N)"
    if ($response -match "^[Yy]$") {
        Add-Content -Path ".env" -Value "`nOPENWEBUI_PROFILE=disabled"
        Write-Host "✓ Disabled Open WebUI, continuing with setup" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Setup cancelled. Please resolve Open WebUI image issue and try again." -ForegroundColor Red
        exit 1
    }
}

# Pull base images
Write-Host "📦 Pulling PostgreSQL..." -ForegroundColor Cyan
docker compose pull postgres

Write-Host "📦 Building Backend..." -ForegroundColor Cyan
docker compose build backend

# Pull Open WebUI with fallback logic
Try-Pull-OpenWebUI

Write-Host ""
Write-Host "✓ All images ready" -ForegroundColor Green

# ... existing docker compose up code ...
```

#### 5.1.5 README.md

**Changes**: Multiple sections need updates

**Section 1: Quick Start** (around line 30):

**Before**:
```markdown
### Quick Start

1. Run the setup script
2. Access API at http://localhost:8000/docs
3. (Optional) Set up Open WebUI following the manual guide
```

**After**:
```markdown
### Quick Start

1. Run the setup script:
   ```bash
   # Linux/Mac
   ./scripts/setup/first_run.sh

   # Windows
   powershell -ExecutionPolicy Bypass -File .\scripts\setup\first_run.ps1
   ```

2. Wait for services to start (2-5 minutes)

3. Access Maestro:
   - **Web UI**: http://localhost:3000 (Open WebUI)
   - **API**: http://localhost:8000/docs (Swagger UI)

4. Create your account in Open WebUI and start chatting!

**Note**: If Open WebUI doesn't start automatically (GHCR access issues), see the [troubleshooting guide](docs/guides/openwebui-setup.md).
```

**Section 2: Architecture Diagram** (around line 50):

**Before**:
```
User → API (Backend) → Local RAG → Ollama
                     → Database
```

**After**:
```
User → Open WebUI → Backend API → Local RAG → Ollama (Host)
   ↓               ↓                         ↓
Browser       Port 8000                Port 11434
Port 3000
                     ↓
                 PostgreSQL
                 Port 5432
```

**Section 3: Alternative Frontends** (around line 85):

**Before**:
```markdown
#### Option 3: Open WebUI (Optional, Manual Setup Required)

See [Open WebUI Setup Guide](docs/guides/openwebui-setup.md)
```

**After**:
```markdown
#### Default Frontend: Open WebUI

Open WebUI runs by default at http://localhost:3000 after setup.

**Troubleshooting**: If Open WebUI doesn't start:
- Check setup script output for image pull errors
- See [Open WebUI Troubleshooting](docs/guides/openwebui-setup.md)

**Disabling Open WebUI**: If you prefer API-only access:
```bash
# Add to .env before running setup:
echo "OPENWEBUI_PROFILE=disabled" >> .env
```

#### Alternative Option: Maestro UI (Development)

A native React UI is in development:
```bash
cd maestro-ui
npm install
npm run dev
# Access at http://localhost:5173
```

**Note**: Maestro UI is not production-ready yet.
```

**Section 4: System Requirements** (around line 120):

**Addition**:
```markdown
### Network Requirements

- **Outbound HTTPS** to download Docker images:
  - ghcr.io (GitHub Container Registry) - preferred
  - docker.io (Docker Hub) - fallback
- **No inbound ports required** (all services run locally)
- **Corporate Networks**: May require proxy configuration for image pulls
```

**Section 5: Environment Variables** (around line 250):

**Addition**:
```markdown
#### Open WebUI Configuration

```bash
OPENWEBUI_PROFILE=default          # Set to "disabled" to disable Open WebUI
OPENWEBUI_IMAGE=ghcr.io/...        # Override image source if needed
WEBUI_PORT=3000                     # Web UI port
WEBUI_SECRET_KEY=change-me          # Session secret (change in production!)
WEBUI_NAME=Maestro AI Assistant     # Display name in UI
WEBUI_AUTH=true                     # Enable authentication (recommended)
```
```

#### 5.1.6 docs/guides/openwebui-setup.md

**Changes**: Restructure from "how to install" to "troubleshooting"

**New Structure**:
```markdown
# Open WebUI Troubleshooting Guide

**Note**: Open WebUI now installs by default. This guide is for troubleshooting issues.

## Expected Behavior

After running the setup script, Open WebUI should:
1. Pull image (ghcr.io or Docker Hub mirror)
2. Start automatically with `docker compose up`
3. Be accessible at http://localhost:3000
4. Connect to Ollama on host system
5. Let you create an account and start chatting

## Common Issues

### Issue 1: Open WebUI Service Not Running

**Symptoms**:
- `docker ps` doesn't show `maestro-openwebui` container
- http://localhost:3000 shows "connection refused"

**Diagnosis**:
```bash
# Check if service is defined
cd infra
docker compose config | grep -A 10 "open-webui"

# Check if disabled in .env
grep OPENWEBUI_PROFILE .env
```

**Solutions**:
- If `OPENWEBUI_PROFILE=disabled`, remove that line from .env
- Restart: `docker compose up -d open-webui`

### Issue 2: Image Pull Failed (GHCR Authentication)

**Symptoms**:
- Setup script shows: "Failed to pull from GHCR"
- Error: "denied: denied"

**Root Cause**: GitHub Container Registry requires authentication

**Solution 1: Authenticate with GHCR (Recommended)**:
```bash
# Create GitHub Personal Access Token (PAT)
# 1. Go to https://github.com/settings/tokens
# 2. Generate new token (classic)
# 3. Select scope: read:packages
# 4. Copy token

# Login to GHCR
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Paste PAT when prompted for password

# Pull image
docker pull ghcr.io/open-webui/open-webui:latest

# Restart setup
./scripts/setup/first_run.sh
```

**Solution 2: Use Docker Hub Mirror**:
```bash
# Pull from verified mirror
docker pull VERIFIED_MIRROR_NAME/open-webui:latest

# Tag as GHCR image
docker tag VERIFIED_MIRROR_NAME/open-webui:latest \
           ghcr.io/open-webui/open-webui:latest

# Start services
cd infra && docker compose up -d
```

**Solution 3: Build from Source**:
```bash
# Clone Open WebUI repository
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# Build image
docker build -t ghcr.io/open-webui/open-webui:latest .

# Return to Maestro and start
cd /path/to/Maestro/infra
docker compose up -d
```

### Issue 3: Open WebUI Can't Connect to Ollama

**Symptoms**:
- Open WebUI loads but shows "Ollama connection error"
- No models appear in model selector

**Diagnosis**:
```bash
# Check if Ollama is running on host
curl http://localhost:11434/api/tags

# Check from within container
docker exec maestro-openwebui curl http://host.docker.internal:11434/api/tags
```

**Solutions**:
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_HOST` in .env: should be `http://host.docker.internal:11434`
- Linux users: May need `http://172.17.0.1:11434` instead
- Restart Open WebUI: `docker compose restart open-webui`

### Issue 4: Port 3000 Already in Use

**Symptoms**:
- Setup fails with "port is already allocated"

**Solutions**:
```bash
# Find process using port 3000
# Windows:
netstat -ano | findstr :3000
# Linux/Mac:
lsof -i :3000

# Option 1: Kill conflicting process
# Option 2: Change port in .env
echo "WEBUI_PORT=3001" >> .env

# Restart
cd infra && docker compose up -d
```

## Manual Installation Options

If automatic installation fails completely:

### Option 1: Docker Hub Alternative Image

**Caution**: Verify trustworthiness before using community mirrors.

```bash
# Example (DO NOT use until verified):
docker pull docker.io/UNVERIFIED_MIRROR/open-webui:latest
docker tag docker.io/UNVERIFIED_MIRROR/open-webui:latest \
           ghcr.io/open-webui/open-webui:latest
```

### Option 2: Disable Open WebUI

If you prefer API-only access:

```bash
# Add to .env
echo "OPENWEBUI_PROFILE=disabled" >> .env

# Remove container if running
cd infra
docker compose down open-webui

# Use Maestro via API
# Docs: http://localhost:8000/docs
```

## Security Considerations

### Changing Default Secret Key

**Important**: Change `WEBUI_SECRET_KEY` before exposing to network.

```bash
# Generate secure random key
openssl rand -hex 32

# Update .env
WEBUI_SECRET_KEY=your-generated-key-here

# Restart Open WebUI
docker compose restart open-webui
```

### Authentication Settings

```bash
# .env settings
WEBUI_AUTH=true                    # Require login (recommended)
WEBUI_ADMIN_EMAIL=admin@domain.com # First user becomes admin
```

### Exposing to Network

By default, Open WebUI is only accessible from localhost. To expose:

**Option 1: Change Port Binding (DANGEROUS)**:
```yaml
# docker-compose.yml
ports:
  - "0.0.0.0:3000:8080"  # Accessible from any IP
```

**Option 2: Reverse Proxy (RECOMMENDED)**:
- Use Nginx/Traefik with HTTPS
- Implement authentication at proxy level
- See [Production Deployment Guide](../production-deployment.md)

## Getting Help

If these solutions don't work:
1. Check logs: `docker compose logs -f open-webui`
2. Review [Deployment Architecture](../deployment-architecture.md)
3. Open issue: https://github.com/lordmuffin/Maestro/issues
4. Include: OS, Docker version, error messages, logs
```

### 5.2 New Documentation Required

#### 5.2.1 docs/guides/production-deployment.md (NEW)

**Purpose**: Guide for deploying Maestro in production with HTTPS, authentication, etc.

**Outline**:
```markdown
# Production Deployment Guide

## Overview
This guide covers deploying Maestro in production environments.

## Prerequisites
- Domain name
- SSL certificate (Let's Encrypt recommended)
- Firewall/security groups configured
- Production-grade secrets

## Deployment Options
### Option 1: Nginx Reverse Proxy
### Option 2: Traefik with Docker
### Option 3: Cloud Provider (AWS/GCP/Azure)

## Security Hardening
- Change all default passwords
- Enable HTTPS only
- Configure firewall rules
- Set up monitoring/logging
- Regular backups

## Scaling Considerations
- Multiple backend replicas
- Database replication
- Load balancing
- CDN for static assets

## Monitoring
- Health check endpoints
- Log aggregation
- Metrics collection
- Alerting rules

## Backup and Recovery
- Database backup schedule
- Volume backup procedures
- Disaster recovery plan

## Maintenance
- Update procedures
- Rollback strategy
- Zero-downtime deployment
```

#### 5.2.2 docs/faq.md (NEW)

**Purpose**: Common questions about Maestro

**Outline**:
```markdown
# Frequently Asked Questions (FAQ)

## General

**Q: What is Maestro?**
A: Maestro is a privacy-first AI executive assistant...

**Q: Do I need cloud APIs?**
A: No, Maestro works entirely locally...

## Installation

**Q: Why isn't Open WebUI starting?**
A: See [Open WebUI Troubleshooting](guides/openwebui-setup.md)

**Q: Can I use Maestro without a web UI?**
A: Yes, set `OPENWEBUI_PROFILE=disabled` in .env

**Q: What are the minimum system requirements?**
A: ...

## Usage

**Q: How do I add my Obsidian vault?**
A: Set `LOCAL_OBSIDIAN_PATH` in .env...

**Q: Can I use cloud LLMs instead of Ollama?**
A: Yes, see [LLM Configuration](llm-configuration.md)

**Q: How do I create custom skills?**
A: See [Phase 4 Skills Framework](phase4_skills_framework.md)

## Troubleshooting

**Q: Port 8000 is already in use**
A: See [Troubleshooting Guide](troubleshooting.md#port-conflicts)

**Q: Ollama connection failed**
A: See [Troubleshooting Guide](troubleshooting.md#ollama-connection-issues)

## Security & Privacy

**Q: Is my data sent to cloud services?**
A: No, unless you explicitly configure cloud LLMs...

**Q: How do I change default passwords?**
A: See [Security Best Practices](guides/production-deployment.md#security)

**Q: Can I use Maestro in a corporate environment?**
A: Yes, but check your organization's policies...
```

### 5.3 Testing Validation

**Required Tests**:

1. **Fresh Installation Test**:
   - Clean system (no Docker images/containers)
   - Run setup script
   - Verify Open WebUI starts and is accessible
   - Verify Ollama connection works
   - Verify can create account and send message

2. **GHCR Failure Test**:
   - Block ghcr.io (via hosts file or firewall)
   - Run setup script
   - Verify fallback to Docker Hub mirror works
   - Verify Open WebUI still starts successfully

3. **Opt-Out Test**:
   - Set `OPENWEBUI_PROFILE=disabled` before setup
   - Run setup script
   - Verify Open WebUI is not started
   - Verify backend still works (API accessible)
   - Verify no errors in logs about missing Open WebUI

4. **Update Test**:
   - Existing installation with Open WebUI disabled
   - Pull latest code with Open WebUI enabled by default
   - Run `docker compose up -d`
   - Verify existing users aren't forced to use Open WebUI

5. **Manual Authentication Test**:
   - Run `docker login ghcr.io`
   - Provide valid GitHub PAT
   - Run setup script
   - Verify GHCR image pulls successfully

6. **Build from Source Test**:
   - Block both ghcr.io and docker.io
   - Choose "build from source" option
   - Verify image builds successfully (may take 10+ minutes)
   - Verify Open WebUI starts with built image

### 5.4 Rollback Plan

If implementation causes issues:

**Phase 1: Immediate Rollback** (within 24 hours of release):
```bash
# Revert docker-compose.yml to commented-out state
git revert <commit-hash>

# Update README.md to indicate temporary issue
echo "⚠ Open WebUI temporarily disabled due to [issue]" > BREAKING_CHANGE.md

# Release hotfix version
```

**Phase 2: Partial Rollback** (if specific feature broken):
- Keep Open WebUI enabled
- Remove automatic fallback logic
- Require manual setup again
- Fix underlying issue

**Phase 3: Documentation Update** (if can't fix):
- Update docs to indicate Open WebUI requires manual setup
- Provide clearer instructions
- Add troubleshooting section

---

## 6. Risks and Mitigation

### 6.1 High Priority Risks

#### Risk 1: Docker Hub Mirror Trustworthiness

**Description**: Using unverified Docker Hub mirrors could introduce security vulnerabilities or malicious code.

**Impact**: HIGH - Could compromise user systems
**Likelihood**: MEDIUM - If we don't properly verify mirrors

**Mitigation**:
1. **Verification Process** (see Section 10.1):
   - Check mirror maintainer reputation
   - Verify image hash matches official builds
   - Review Dockerfile if available
   - Test in isolated environment
   - Monitor for unexpected behavior

2. **Fallback Chain Priority**:
   - Always try GHCR first
   - Only use Docker Hub as fallback
   - Prefer "build from source" over untrusted mirrors

3. **User Notification**:
   - Setup script clearly indicates which image source was used
   - Warn if using non-official source
   - Provide option to cancel and use manual authentication

**Status**: 🔴 **BLOCKER** - Must verify mirror before implementation

#### Risk 2: Increased Setup Failure Rate

**Description**: Adding automatic fallback logic increases setup script complexity, which could introduce new failure modes.

**Impact**: MEDIUM - Users can't complete setup
**Likelihood**: MEDIUM - Complex shell scripts are error-prone

**Mitigation**:
1. **Extensive Testing**:
   - Test on Windows, Linux, macOS
   - Test with/without GHCR access
   - Test with/without internet access
   - Test with corporate proxies

2. **Clear Error Messages**:
   - Every failure path provides next steps
   - Logs detailed information for debugging
   - Points users to troubleshooting docs

3. **Opt-Out Escape Hatch**:
   - Users can disable Open WebUI and continue
   - Setup doesn't fail completely if Open WebUI fails

4. **Monitoring**:
   - Track setup success/failure rates via telemetry (opt-in)
   - GitHub issues tagged with "setup-failure"

#### Risk 3: Breaking Existing Installations

**Description**: Enabling Open WebUI by default might break existing installations that customized their setup.

**Impact**: MEDIUM - Frustration for existing users
**Likelihood**: LOW - docker-compose.yml changes are additive

**Mitigation**:
1. **Backward Compatibility**:
   - Use docker-compose profiles (not hard dependencies)
   - Environment variable overrides don't break existing .env files
   - Volume names remain unchanged

2. **Release Notes**:
   - Prominently document change in CHANGELOG
   - Provide migration instructions
   - Mark as "breaking change" if necessary

3. **Gradual Rollout**:
   - Tag release as beta/RC first
   - Gather feedback before marking stable
   - Give users time to test upgrades

4. **Rollback Documentation**:
   - Provide clear instructions to disable Open WebUI
   - Document how to revert to previous behavior

### 6.2 Medium Priority Risks

#### Risk 4: Corporate Firewall Issues

**Description**: Some corporate networks block both ghcr.io and docker.io, making any image pull fail.

**Impact**: LOW - Affects subset of users
**Likelihood**: MEDIUM - Corporate networks often restrict Docker registries

**Mitigation**:
1. **Pre-flight Connectivity Check**:
   ```bash
   check_registry_access() {
     curl -Is https://ghcr.io | head -n 1
     curl -Is https://docker.io | head -n 1
   }
   ```

2. **Clear Guidance**:
   - Document proxy configuration steps
   - Provide alternative: build from source
   - Suggest: download image on personal machine, save to tar, transfer

3. **Offline Installation Option**:
   ```bash
   # Save image on internet-connected machine
   docker save ghcr.io/open-webui/open-webui:latest -o openwebui.tar

   # Transfer to air-gapped machine
   # Load image
   docker load -i openwebui.tar
   ```

#### Risk 5: Image Version Pinning

**Description**: Using `:latest` tag means updates happen automatically, potentially introducing breaking changes.

**Impact**: LOW - Users get breaking updates
**Likelihood**: MEDIUM - Open WebUI does release breaking changes occasionally

**Mitigation**:
1. **Pin to Specific Version**:
   - Change `.env.example` to pin version: `OPENWEBUI_IMAGE=ghcr.io/open-webui/open-webui:v0.1.124`
   - Update version in release notes when new stable version available

2. **Version Compatibility Matrix**:
   - Document which Open WebUI versions work with which Maestro versions
   - Test each Open WebUI release before recommending

3. **User Control**:
   - Allow `OPENWEBUI_IMAGE` override in .env
   - Document how to pin specific version

#### Risk 6: Resource Consumption

**Description**: Enabling Open WebUI by default increases resource usage (RAM, disk, CPU).

**Impact**: LOW - Slower performance on low-end systems
**Likelihood**: MEDIUM - Open WebUI uses ~500MB RAM

**Mitigation**:
1. **System Requirements Documentation**:
   - Update README to specify: "12GB+ RAM recommended with Open WebUI"
   - Provide guidance: "For systems with <8GB RAM, disable Open WebUI"

2. **Resource Limits in Docker**:
   ```yaml
   open-webui:
     deploy:
       resources:
         limits:
           memory: 1G
           cpus: '1.0'
   ```

3. **Opt-Out Remains Easy**:
   - One environment variable to disable
   - Clear documentation on when to disable

### 6.3 Risk Summary Matrix

| Risk | Impact | Likelihood | Priority | Mitigation Status |
|------|--------|------------|----------|-------------------|
| Docker Hub Mirror Trust | HIGH | MEDIUM | 🔴 CRITICAL | BLOCKED - Needs verification |
| Setup Failure Rate | MEDIUM | MEDIUM | 🟡 HIGH | In progress - testing plan |
| Breaking Existing Installs | MEDIUM | LOW | 🟡 MEDIUM | Mitigated - backward compat |
| Corporate Firewalls | LOW | MEDIUM | 🟢 LOW | Mitigated - docs + alternatives |
| Version Pinning | LOW | MEDIUM | 🟢 LOW | Mitigated - pin specific version |
| Resource Consumption | LOW | MEDIUM | 🟢 LOW | Mitigated - docs + limits |

---

## 7. Testing Requirements

### 7.1 Test Environments

**Required Test Platforms**:
1. Windows 11 + Docker Desktop (latest)
2. Ubuntu 22.04 + Docker Engine + Docker Compose V2
3. macOS Ventura + Docker Desktop (latest)
4. Ubuntu 20.04 + Docker Engine + Docker Compose V1 (legacy)

**Network Scenarios**:
- Unrestricted internet access (home network)
- Corporate proxy environment
- Firewall blocking ghcr.io
- Firewall blocking both ghcr.io and docker.io
- Offline/air-gapped environment

**System Resource Scenarios**:
- High-end: 32GB RAM, 8 CPU cores
- Mid-range: 16GB RAM, 4 CPU cores
- Low-end: 8GB RAM, 2 CPU cores

### 7.2 Test Cases

#### Test Suite 1: Fresh Installation

**Test 1.1: Successful GHCR Pull**
```
Preconditions:
- Clean system (no existing Maestro installation)
- Internet access to ghcr.io
- No GitHub authentication configured

Steps:
1. Clone Maestro repository
2. Run first_run.sh (or .ps1)
3. Monitor setup output

Expected Results:
- ✓ Script pulls ghcr.io/open-webui/open-webui:latest
- ✓ Script shows "Successfully pulled from GitHub Container Registry"
- ✓ docker-compose up succeeds
- ✓ Open WebUI container starts
- ✓ http://localhost:3000 loads Open WebUI
- ✓ Can create account and send message
- ✓ Ollama connection works

Pass Criteria: All checks pass
```

**Test 1.2: GHCR Fails, Docker Hub Succeeds**
```
Preconditions:
- Clean system
- Block ghcr.io via hosts file (127.0.0.1 ghcr.io)
- Docker Hub accessible

Steps:
1. Clone repository
2. Run first_run.sh
3. Monitor fallback behavior

Expected Results:
- ✓ Script attempts ghcr.io pull (fails silently)
- ✓ Script shows "Failed to pull from GHCR, trying fallback"
- ✓ Script pulls from Docker Hub mirror
- ✓ Script tags mirror as ghcr.io image
- ✓ docker-compose up succeeds
- ✓ Open WebUI works normally

Pass Criteria: All checks pass
```

**Test 1.3: Both Registries Fail, User Cancels**
```
Preconditions:
- Clean system
- Block both ghcr.io and docker.io

Steps:
1. Run first_run.sh
2. When prompted "Continue without Open WebUI?", answer "N"

Expected Results:
- ✓ Script shows detailed troubleshooting options
- ✓ Script exits with error code 1
- ✓ No containers are started
- ✓ User can resolve issue and re-run

Pass Criteria: All checks pass
```

**Test 1.4: Both Registries Fail, User Continues**
```
Preconditions:
- Clean system
- Block both registries

Steps:
1. Run first_run.sh
2. When prompted "Continue without Open WebUI?", answer "Y"

Expected Results:
- ✓ Script adds OPENWEBUI_PROFILE=disabled to .env
- ✓ Script continues with backend and postgres
- ✓ Backend starts successfully
- ✓ http://localhost:8000/docs works
- ✓ Open WebUI container NOT started
- ✓ No errors in logs about Open WebUI

Pass Criteria: All checks pass
```

**Test 1.5: Pre-configured Opt-Out**
```
Preconditions:
- Clean system
- .env contains OPENWEBUI_PROFILE=disabled before running script

Steps:
1. Run first_run.sh

Expected Results:
- ✓ Script detects OPENWEBUI_PROFILE=disabled
- ✓ Script skips Open WebUI image pull entirely
- ✓ No fallback logic triggered
- ✓ Backend starts successfully
- ✓ Open WebUI container not started

Pass Criteria: All checks pass
```

#### Test Suite 2: Upgrade Scenarios

**Test 2.1: Upgrade from Version with Open WebUI Disabled**
```
Preconditions:
- Existing Maestro installation
- Open WebUI commented out in docker-compose.yml
- .env does NOT contain OPENWEBUI_PROFILE

Steps:
1. git pull (get new code with Open WebUI enabled)
2. docker compose pull
3. docker compose up -d

Expected Results:
- ✓ New Open WebUI service starts automatically
- ✓ Existing backend/postgres containers not recreated
- ✓ No data loss
- ✓ http://localhost:3000 works
- ✓ Backend still works at http://localhost:8000

Pass Criteria: All checks pass
```

**Test 2.2: Upgrade with Explicit Disable**
```
Preconditions:
- Existing installation
- .env contains OPENWEBUI_PROFILE=disabled

Steps:
1. git pull
2. docker compose up -d

Expected Results:
- ✓ Open WebUI service not started
- ✓ No errors in docker compose output
- ✓ Backend still works
- ✓ User's preference to disable is respected

Pass Criteria: All checks pass
```

#### Test Suite 3: Manual Override

**Test 3.1: Custom Image Source**
```
Preconditions:
- Clean system
- .env contains: OPENWEBUI_IMAGE=custom-registry.com/openwebui:v1.2.3

Steps:
1. Run first_run.sh
2. docker compose up -d

Expected Results:
- ✓ Script/compose attempts to pull custom image
- ✓ No fallback to ghcr.io or docker.io
- ✓ If custom image exists, Open WebUI starts
- ✓ If custom image doesn't exist, clear error message

Pass Criteria: All checks pass
```

**Test 3.2: Manual GHCR Authentication**
```
Preconditions:
- Clean system
- Run: docker login ghcr.io (with valid GitHub PAT)

Steps:
1. Run first_run.sh

Expected Results:
- ✓ GHCR pull succeeds (no fallback needed)
- ✓ Script shows "Successfully pulled from GitHub Container Registry"
- ✓ Open WebUI starts normally

Pass Criteria: All checks pass
```

#### Test Suite 4: Error Handling

**Test 4.1: Port Conflict**
```
Preconditions:
- Port 3000 already in use (run: python -m http.server 3000)

Steps:
1. Run first_run.sh
2. docker compose up -d

Expected Results:
- ✓ docker compose shows error: "port is already allocated"
- ✓ Error message points to troubleshooting guide
- ✓ User can resolve (change WEBUI_PORT or kill process)

Pass Criteria: Clear error, resolution path documented
```

**Test 4.2: Out of Disk Space**
```
Preconditions:
- System with <2GB free disk space

Steps:
1. Run first_run.sh

Expected Results:
- ✓ Docker pull fails with "no space left on device"
- ✓ Script shows clear error
- ✓ Instructions to free space provided

Pass Criteria: Clear error, actionable guidance
```

#### Test Suite 5: Integration Tests

**Test 5.1: Open WebUI to Ollama Connection**
```
Preconditions:
- Fresh installation with Open WebUI running
- Ollama running on host with llama3:8b pulled

Steps:
1. Browse to http://localhost:3000
2. Create account
3. Check model selector dropdown
4. Send message: "Hello, please respond with 'test successful'"

Expected Results:
- ✓ Model selector shows llama3:8b
- ✓ Message sends without error
- ✓ LLM response received
- ✓ Response contains "test successful"

Pass Criteria: All checks pass
```

**Test 5.2: Open WebUI to Backend Connection**
```
Preconditions:
- Fresh installation

Steps:
1. Open browser developer tools (Network tab)
2. Browse to http://localhost:3000
3. Send a message
4. Check network requests

Expected Results:
- ✓ Requests to http://localhost:3000/api/* succeed
- ✓ No CORS errors
- ✓ Backend logs show Open WebUI requests

Pass Criteria: All checks pass
```

### 7.3 Performance Testing

**Test P.1: Setup Time**
```
Measure time from running first_run.sh to services ready

Acceptance Criteria:
- GHCR pull: <5 minutes total setup time
- Docker Hub fallback: <6 minutes total setup time
- Build from source: <15 minutes total setup time

Measurement:
- Record timestamps at: start, image pulled, services up, health check passed
```

**Test P.2: Resource Usage**
```
Measure system resources with Open WebUI enabled vs disabled

Metrics:
- RAM usage (docker stats)
- CPU usage (docker stats)
- Disk usage (docker system df)

Acceptance Criteria:
- With Open WebUI: <2GB total RAM, <50% CPU average
- Open WebUI container: <500MB RAM, <20% CPU average
```

### 7.4 Security Testing

**Test S.1: Default Secret Key Warning**
```
Verify users are warned about default secret key

Steps:
1. Fresh installation (don't modify WEBUI_SECRET_KEY)
2. Check setup script output
3. Check Open WebUI logs

Expected:
- ✓ Setup script warns about changing secret key
- ✓ README has prominent warning
- ✓ Documentation includes key generation command

Pass Criteria: Warning displayed in 3 places
```

**Test S.2: Authentication Enabled by Default**
```
Verify Open WebUI requires login

Steps:
1. Fresh installation
2. Browse to http://localhost:3000
3. Attempt to use without creating account

Expected:
- ✓ Redirected to signup/login page
- ✓ Cannot access chat without account
- ✓ WEBUI_AUTH=true in default .env.example

Pass Criteria: All checks pass
```

### 7.5 Documentation Testing

**Test D.1: README Accuracy**
```
Steps:
1. Follow README Quick Start instructions exactly
2. Note any discrepancies

Expected:
- ✓ All commands work as documented
- ✓ All URLs are correct
- ✓ Screenshots match actual UI
- ✓ Expected behavior matches reality

Pass Criteria: Zero discrepancies
```

**Test D.2: Troubleshooting Guide Coverage**
```
Steps:
1. Review all errors encountered in testing
2. Check if each has entry in troubleshooting guide

Expected:
- ✓ Every tested error has troubleshooting entry
- ✓ Solutions are accurate and complete
- ✓ Examples include actual command output

Pass Criteria: 100% error coverage
```

### 7.6 Acceptance Criteria Summary

**Must Pass Before Release**:
- [ ] All Test Suite 1 tests pass (Fresh Installation)
- [ ] At least 90% success rate on GHCR pull OR Docker Hub fallback works
- [ ] All opt-out tests pass (users can disable Open WebUI)
- [ ] No breaking changes to existing installations (Test Suite 2)
- [ ] Open WebUI to Ollama connection works (Test 5.1)
- [ ] Documentation tested and accurate (Test Suite D)
- [ ] Docker Hub mirror verified trustworthy (Section 10.1)

**Should Pass Before Release**:
- [ ] All Test Suite 3 tests pass (Manual Override)
- [ ] All Test Suite 4 tests pass (Error Handling)
- [ ] Performance benchmarks met (Test P.1, P.2)
- [ ] Security tests pass (Test Suite S)

**Can Be Fixed Post-Release**:
- Edge case platform compatibility issues
- Performance optimizations
- Documentation improvements based on user feedback

---

## 8. Implementation Roadmap

### 8.1 Timeline Overview

**Total Duration**: 17 days
**Release Target**: Day 18

```
Week 1: Research & Core Implementation (Days 1-7)
Week 2: Testing & Documentation (Days 8-14)
Week 3: Validation & Release (Days 15-17)
Day 18: Release
```

### 8.2 Detailed Schedule

#### Phase 1: Research & Verification (Days 1-3)

**Day 1: Docker Hub Mirror Verification**
- **Owner**: Security/DevOps lead
- **Tasks**:
  - [ ] Research available Docker Hub mirrors for Open WebUI
  - [ ] Verify maintainer reputation (GitHub profiles, community presence)
  - [ ] Compare image hashes with official GHCR builds
  - [ ] Test images in isolated environment
  - [ ] Document findings in `docs/security/mirror-verification.md`
- **Deliverables**:
  - Verified mirror name OR decision to skip Docker Hub fallback
  - Security verification report
- **Blockers**: If no trustworthy mirror found, adjust plan to use build-from-source as fallback
- **Time**: 4-6 hours

**Day 2: Test Environment Setup**
- **Owner**: QA/Testing lead
- **Tasks**:
  - [ ] Set up test VMs (Windows, Ubuntu, macOS)
  - [ ] Configure network scenarios (proxy, firewall rules)
  - [ ] Create test checklist from Section 7
  - [ ] Set up automated test scripts (bash/powershell)
- **Deliverables**:
  - Test environments ready
  - Test automation scripts
- **Time**: 4-6 hours

**Day 3: Implementation Planning**
- **Owner**: Project lead
- **Tasks**:
  - [ ] Review this plan with team
  - [ ] Assign tasks to team members
  - [ ] Create GitHub issues for each change
  - [ ] Set up project board for tracking
  - [ ] Get stakeholder approval to proceed
- **Deliverables**:
  - Team assignments
  - GitHub issues created
  - Go/no-go decision
- **Time**: 2-3 hours

#### Phase 2: Core Implementation (Days 4-7)

**Day 4: docker-compose.yml Changes**
- **Owner**: DevOps engineer
- **Tasks**:
  - [ ] Uncomment Open WebUI service
  - [ ] Add OPENWEBUI_PROFILE support
  - [ ] Add OPENWEBUI_IMAGE variable support
  - [ ] Update volume configuration
  - [ ] Test locally with `docker compose config`
- **Deliverables**:
  - Updated `infra/docker-compose.yml`
  - Local verification that service starts
- **Testing**: Manual start/stop, verify env vars work
- **Time**: 2-3 hours

**Day 5: Setup Scripts - Bash**
- **Owner**: Backend engineer
- **Tasks**:
  - [ ] Implement `try_pull_openwebui()` function in first_run.sh
  - [ ] Add fallback logic (GHCR → Docker Hub → prompt user)
  - [ ] Add messaging for each scenario
  - [ ] Test on Linux and macOS
- **Deliverables**:
  - Updated `scripts/setup/first_run.sh`
  - Test results from Linux/macOS
- **Testing**: Test Suite 1.1, 1.2, 1.3, 1.4
- **Time**: 4-5 hours

**Day 6: Setup Scripts - PowerShell**
- **Owner**: Backend engineer
- **Tasks**:
  - [ ] Port bash logic to PowerShell in first_run.ps1
  - [ ] Handle Windows-specific path/encoding issues
  - [ ] Test on Windows 10 and 11
- **Deliverables**:
  - Updated `scripts/setup/first_run.ps1`
  - Test results from Windows
- **Testing**: Test Suite 1.1-1.4 on Windows
- **Time**: 4-5 hours

**Day 7: Environment Configuration**
- **Owner**: Backend engineer
- **Tasks**:
  - [ ] Update `.env.example` with all Open WebUI variables
  - [ ] Add detailed comments explaining each variable
  - [ ] Set secure defaults (random secret key placeholder)
  - [ ] Verify docker-compose loads all variables
- **Deliverables**:
  - Updated `.env.example`
  - Verification that all vars work
- **Testing**: Manual env var validation
- **Time**: 2-3 hours

#### Phase 3: Documentation (Days 8-10)

**Day 8: README Updates**
- **Owner**: Technical writer / maintainer
- **Tasks**:
  - [ ] Update Quick Start section
  - [ ] Update Architecture diagram
  - [ ] Update Alternative Frontends section
  - [ ] Add Network Requirements
  - [ ] Update Environment Variables table
  - [ ] Add troubleshooting link
- **Deliverables**:
  - Updated `README.md`
  - Reviewed by at least 2 team members
- **Testing**: Test D.1 (follow README exactly)
- **Time**: 3-4 hours

**Day 9: Troubleshooting Guide Restructure**
- **Owner**: Technical writer
- **Tasks**:
  - [ ] Restructure `docs/guides/openwebui-setup.md`
  - [ ] Add "Expected Behavior" section
  - [ ] Add all common issues from testing
  - [ ] Add manual installation options
  - [ ] Add security considerations
- **Deliverables**:
  - Updated `docs/guides/openwebui-setup.md`
- **Testing**: Test D.2 (coverage of all errors)
- **Time**: 3-4 hours

**Day 10: Additional Documentation**
- **Owner**: Technical writer
- **Tasks**:
  - [ ] Create `docs/guides/production-deployment.md` (outline)
  - [ ] Create `docs/faq.md`
  - [ ] Update `docs/deployment-architecture.md` if needed
  - [ ] Update `docs/phase4_skills_framework.md` Open WebUI section
- **Deliverables**:
  - New/updated documentation files
- **Time**: 3-4 hours

#### Phase 4: Testing (Days 11-14)

**Day 11: Fresh Installation Testing**
- **Owner**: QA engineer
- **Tasks**:
  - [ ] Run Test Suite 1 (all 5 tests)
  - [ ] Test on Windows, Linux, macOS
  - [ ] Test with unrestricted network
  - [ ] Document all failures
- **Deliverables**:
  - Test results spreadsheet
  - Bug reports for any failures
- **Blockers**: Any Test Suite 1 failures are high priority bugs
- **Time**: 6-8 hours

**Day 12: Upgrade & Override Testing**
- **Owner**: QA engineer
- **Tasks**:
  - [ ] Run Test Suite 2 (upgrade scenarios)
  - [ ] Run Test Suite 3 (manual overrides)
  - [ ] Test on all platforms
  - [ ] Document any breaking changes
- **Deliverables**:
  - Test results
  - Migration guide if needed
- **Time**: 4-5 hours

**Day 13: Error Handling & Integration Testing**
- **Owner**: QA engineer
- **Tasks**:
  - [ ] Run Test Suite 4 (error handling)
  - [ ] Run Test Suite 5 (integration)
  - [ ] Test corporate proxy scenario
  - [ ] Test firewall scenarios
- **Deliverables**:
  - Test results
  - Bug reports
- **Time**: 4-5 hours

**Day 14: Performance & Security Testing**
- **Owner**: QA engineer
- **Tasks**:
  - [ ] Run performance tests (Test P.1, P.2)
  - [ ] Run security tests (Test S.1, S.2)
  - [ ] Document baseline metrics
  - [ ] Verify resource limits are reasonable
- **Deliverables**:
  - Performance benchmarks
  - Security verification
- **Time**: 3-4 hours

#### Phase 5: Bug Fixes & Validation (Days 15-17)

**Day 15: Bug Fixing**
- **Owner**: Development team
- **Tasks**:
  - [ ] Triage all bugs from testing
  - [ ] Fix critical (P0) bugs
  - [ ] Fix high priority (P1) bugs
  - [ ] Document known issues for P2/P3 bugs
- **Deliverables**:
  - Bug fixes committed
  - Known issues documented
- **Time**: Full day

**Day 16: Regression Testing**
- **Owner**: QA engineer
- **Tasks**:
  - [ ] Re-run all failed tests after fixes
  - [ ] Verify no new regressions introduced
  - [ ] Get sign-off from QA lead
- **Deliverables**:
  - Final test results
  - QA approval
- **Time**: 4-6 hours

**Day 17: Release Preparation**
- **Owner**: Release manager
- **Tasks**:
  - [ ] Write CHANGELOG entry
  - [ ] Tag release candidate (vX.Y.Z-rc1)
  - [ ] Build and push Docker images (if applicable)
  - [ ] Prepare release notes
  - [ ] Get final approvals from stakeholders
- **Deliverables**:
  - Release candidate tagged
  - Release notes drafted
  - All approvals obtained
- **Time**: 2-3 hours

#### Phase 6: Release (Day 18)

**Day 18: Public Release**
- **Owner**: Project maintainer
- **Tasks**:
  - [ ] Merge feature branch to main
  - [ ] Tag final release (vX.Y.Z)
  - [ ] Publish release on GitHub
  - [ ] Update documentation site (if applicable)
  - [ ] Announce release (Discord, Twitter, Reddit, etc.)
  - [ ] Monitor for issues in first 24 hours
- **Deliverables**:
  - Public release live
  - Announcement published
- **Time**: 2-3 hours + monitoring

### 8.3 Resource Requirements

**Team Composition**:
- 1x Project Lead (part-time, planning & coordination)
- 1x DevOps Engineer (Days 4-7, 15)
- 1x Backend Engineer (Days 5-7, 15)
- 1x QA Engineer (Days 2, 11-14, 16)
- 1x Technical Writer (Days 8-10)
- 1x Security Reviewer (Day 1, 14)

**Total Effort Estimate**: ~10-12 person-days

**External Dependencies**:
- GitHub (for repository, issues, releases)
- Docker Hub (for mirror verification and fallback)
- Test infrastructure (VMs or cloud instances)

### 8.4 Milestones & Checkpoints

**Milestone 1: Go/No-Go Decision (End of Day 3)**
- Criteria: Docker Hub mirror verified OR decision to use build-from-source
- Decision: Proceed to implementation or abort plan

**Milestone 2: Core Implementation Complete (End of Day 7)**
- Criteria: All code changes committed, local testing passed
- Decision: Proceed to documentation or fix issues

**Milestone 3: Documentation Complete (End of Day 10)**
- Criteria: All docs written and reviewed
- Decision: Proceed to testing

**Milestone 4: Testing Complete (End of Day 14)**
- Criteria: All test suites run, results documented
- Decision: Proceed to bug fixing or abort release

**Milestone 5: QA Sign-Off (End of Day 16)**
- Criteria: All P0/P1 bugs fixed, regression tests passed
- Decision: Proceed to release or delay for more fixes

**Milestone 6: Release (Day 18)**
- Criteria: All approvals obtained
- Decision: Release or postpone

---

## 9. Decision Summary

### 9.1 Key Decisions Made

**Decision 1: Enable Open WebUI by Default**
- **Rationale**: Users expect modern applications to have web UIs
- **Alternative Considered**: Keep manual setup
- **Trade-off**: Increased complexity vs better UX
- **Approval**: TBD (needs stakeholder sign-off)

**Decision 2: Hybrid Fallback Approach**
- **Rationale**: Maximizes success rate across different network environments
- **Alternative Considered**: GHCR-only with manual auth instructions
- **Trade-off**: Script complexity vs reliability
- **Approval**: Recommended by this plan

**Decision 3: Opt-Out via Environment Variable**
- **Rationale**: Respects user choice, maintains flexibility
- **Alternative Considered**: Always force Open WebUI
- **Trade-off**: None (opt-out is strictly beneficial)
- **Approval**: Recommended by this plan

**Decision 4: Docker Compose Profiles for Disable**
- **Rationale**: Clean way to conditionally enable/disable services
- **Alternative Considered**: Separate docker-compose files
- **Trade-off**: Requires Docker Compose 1.28+ (released 2020)
- **Approval**: Recommended by this plan

**Decision 5: Verify Docker Hub Mirror Before Use**
- **Rationale**: Security and trustworthiness are paramount
- **Alternative Considered**: Use any available mirror
- **Trade-off**: Delays implementation vs protects users
- **Approval**: MANDATORY requirement

### 9.2 Open Questions

**Question 1: Should we support build-from-source fallback?**
- **Context**: If both GHCR and Docker Hub fail
- **Options**:
  - A) Prompt user to build from source (complex, slow)
  - B) Fail and require manual intervention
  - C) Continue without Open WebUI
- **Recommendation**: Option C (continue without UI) with clear instructions
- **Needs Input From**: Project lead, community feedback

**Question 2: Should we add telemetry for image pull success rates?**
- **Context**: Would help us understand which fallback is used most
- **Options**:
  - A) Add opt-in telemetry
  - B) No telemetry (trust GitHub issue reports)
- **Recommendation**: Option B (avoid telemetry complexity, respect privacy)
- **Needs Input From**: Privacy policy, community sentiment

**Question 3: Should we create automated setup tests in CI/CD?**
- **Context**: Would catch setup script regressions automatically
- **Options**:
  - A) Add GitHub Actions workflow to test setup scripts
  - B) Rely on manual testing before releases
- **Recommendation**: Option A (if time permits, Phase 2 of this plan)
- **Needs Input From**: DevOps lead, CI/CD availability

**Question 4: Should we update the project tagline/description?**
- **Context**: Current description doesn't mention web UI
- **Current**: "Privacy-first AI executive assistant with local RAG"
- **Proposed**: "Privacy-first AI executive assistant with web UI and local RAG"
- **Recommendation**: Update (aligns with new default behavior)
- **Needs Input From**: Project lead, marketing/communications

### 9.3 Deferred Decisions (Post-Implementation)

**Deferred 1: Migrate from Ollama on Host to Containerized Ollama**
- **Why Deferred**: Separate concern, requires separate planning
- **Future Consideration**: GPU passthrough improvements might make containerized Ollama viable

**Deferred 2: Maestro Native UI Production-Ready**
- **Why Deferred**: Significant development effort, out of scope
- **Future Consideration**: Could replace Open WebUI eventually

**Deferred 3: Self-Hosted Docker Registry for Air-Gapped Deployments**
- **Why Deferred**: Niche use case, adds significant complexity
- **Future Consideration**: Document as advanced deployment option

---

## 10. Open Items and Blockers

### 10.1 Critical Blocker: Docker Hub Mirror Verification

**Status**: 🔴 **BLOCKING IMPLEMENTATION**

**Required Actions**:
1. **Identify Candidate Mirrors**:
   ```bash
   # Search Docker Hub for Open WebUI mirrors
   docker search open-webui

   # Example candidates (DO NOT USE until verified):
   # - docker.io/openwebui/open-webui (check if official)
   # - docker.io/<community-maintainer>/open-webui
   ```

2. **Verify Official Status**:
   - Check Open WebUI GitHub repository for official Docker Hub link
   - Look for Docker Hub documentation in Open WebUI docs
   - Contact Open WebUI maintainers to confirm

3. **Verify Image Integrity**:
   ```bash
   # Pull both images
   docker pull ghcr.io/open-webui/open-webui:latest
   docker pull docker.io/CANDIDATE/open-webui:latest

   # Export images
   docker save ghcr.io/open-webui/open-webui:latest -o ghcr_image.tar
   docker save docker.io/CANDIDATE/open-webui:latest -o dockerhub_image.tar

   # Compare sizes (should be similar)
   ls -lh *.tar

   # Extract and compare layer hashes
   tar -xf ghcr_image.tar manifest.json
   cat manifest.json | jq '.[] | .Layers'

   # Compare with Docker Hub image
   # Layer hashes should match if same build
   ```

4. **Security Scan**:
   ```bash
   # Scan both images with Trivy or similar
   trivy image ghcr.io/open-webui/open-webui:latest
   trivy image docker.io/CANDIDATE/open-webui:latest

   # Compare vulnerabilities (should be identical)
   ```

5. **Maintainer Verification**:
   - Research Docker Hub user/organization
   - Check for verified publisher badge
   - Review other images published (reputation check)
   - Look for evidence of automated builds from GitHub

6. **Functional Testing**:
   ```bash
   # Test Docker Hub image in isolation
   docker run -d --name test-openwebui \
     -p 3000:8080 \
     -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
     docker.io/CANDIDATE/open-webui:latest

   # Verify it works
   curl http://localhost:3000

   # Test Ollama connection
   # Open browser, create account, send message

   # Check for unexpected network traffic
   # Review logs for suspicious behavior
   ```

7. **Document Findings**:
   - Create `docs/security/mirror-verification.md` with results
   - Decision: Use mirror / Don't use mirror / Use build-from-source

**If No Trustworthy Mirror Found**:
- Remove Docker Hub fallback from setup scripts
- Change fallback to: "Continue without UI" + instructions
- Update this plan to remove mirror references

**Timeline**: Must complete by Day 3 of implementation roadmap

### 10.2 Medium Priority: Test Infrastructure

**Status**: 🟡 **NEEDED FOR TESTING PHASE**

**Required Actions**:
- Set up Windows 11 VM (Hyper-V, VirtualBox, or cloud)
- Set up Ubuntu 22.04 VM
- Set up macOS VM (or physical Mac hardware)
- Configure network scenarios (proxy, firewall rules)

**Options**:
- Option A: Use cloud VMs (AWS EC2, GCP, Azure)
- Option B: Use local VMs on developer machines
- Option C: Use GitHub Actions runners (Linux only)

**Recommendation**: Option A (cloud VMs) for consistency

**Timeline**: Must complete by Day 2 of implementation roadmap

**Budget Estimate**: ~$50-100 for 2 weeks of cloud VMs

### 10.3 Low Priority: PowerShell Script UTF-8 Encoding

**Status**: 🟢 **INFORMATIONAL**

**Context**: Previous issues with curly quotes in PowerShell scripts

**Prevention**:
- Ensure all PowerShell scripts saved with UTF-8 encoding (no BOM)
- Use straight quotes (`'` and `"`) not curly quotes (`'`, `'`, `"`, `"`)
- Test PowerShell scripts on Windows before committing

**Verification Command**:
```bash
# Check for curly quotes
grep -n '[''"""]' scripts/setup/first_run.ps1
```

### 10.4 Monitoring: GitHub Issues

**Post-Release Monitoring**:
- Create GitHub issue template: "Open WebUI Setup Failed"
- Tag all Open WebUI setup issues with `openwebui` label
- Weekly review of issues for patterns
- Track setup success rate based on issue frequency

**Template Preview**:
```markdown
## Open WebUI Setup Issue

**Describe the issue:**
[What went wrong during setup?]

**Setup script output:**
```
[Paste output from first_run.sh or first_run.ps1]
```

**Environment:**
- OS: [Windows 11 / Ubuntu 22.04 / macOS Ventura / etc.]
- Docker version: [Run: docker --version]
- Setup script: [first_run.sh or first_run.ps1]
- Image source: [GHCR / Docker Hub / Unknown]

**Expected behavior:**
[What did you expect to happen?]

**Actual behavior:**
[What actually happened?]

**Logs:**
```bash
docker compose logs open-webui
```

**Screenshots:**
[If applicable]
```

---

## 11. Appendices

### Appendix A: Complete File Checklist

**Modified Files**:
- [ ] `infra/docker-compose.yml` - Uncomment and update Open WebUI service
- [ ] `.env.example` - Add comprehensive Open WebUI configuration
- [ ] `scripts/setup/first_run.sh` - Add fallback logic
- [ ] `scripts/setup/first_run.ps1` - Add fallback logic (PowerShell)
- [ ] `README.md` - Update Quick Start, Architecture, Alternatives, Requirements
- [ ] `docs/guides/openwebui-setup.md` - Restructure as troubleshooting guide
- [ ] `docs/deployment-architecture.md` - Note Open WebUI is now default
- [ ] `docs/phase4_skills_framework.md` - Update Open WebUI section
- [ ] `docs/llm-configuration.md` - Update references to default UI

**New Files**:
- [ ] `docs/guides/production-deployment.md` - Production deployment guide
- [ ] `docs/faq.md` - Frequently Asked Questions
- [ ] `docs/security/mirror-verification.md` - Docker Hub mirror verification report
- [ ] `.github/ISSUE_TEMPLATE/openwebui-setup-issue.md` - GitHub issue template

**Unchanged Files** (for reference):
- `infra/docker/backend/Dockerfile` - No changes needed
- `backend/*` - No backend code changes needed
- `maestro-ui/*` - Separate project, no changes

### Appendix B: Environment Variables Reference

**All Open WebUI-Related Environment Variables**:

```bash
#==============================================
# Open WebUI Configuration
#==============================================

# Service Control
OPENWEBUI_PROFILE=default              # Set to "disabled" to disable Open WebUI
OPENWEBUI_IMAGE=ghcr.io/open-webui/open-webui:latest  # Override image source

# Network
WEBUI_PORT=3000                         # External port for Open WebUI

# Authentication
WEBUI_SECRET_KEY=your-secret-here       # Session secret (CHANGE IN PRODUCTION!)
WEBUI_AUTH=true                         # Enable authentication
WEBUI_ADMIN_EMAIL=                      # First user becomes admin (optional)

# Display
WEBUI_NAME=Maestro AI Assistant         # Displayed name in UI

# Backend Connection (usually defaults are fine)
OLLAMA_BASE_URL=http://host.docker.internal:11434  # Ollama connection
WEBUI_DATA_DIR=/app/backend/data        # Data directory (inside container)

# Logging
WEBUI_LOG_LEVEL=info                    # Log level (debug, info, warning, error)

# Advanced (usually not needed)
WEBUI_ENABLE_SIGNUP=true                # Allow new user signups
WEBUI_MAX_UPLOAD_SIZE=10MB              # Max file upload size
WEBUI_SESSION_TIMEOUT=3600              # Session timeout in seconds
```

### Appendix C: Docker Compose Profiles Usage

**Understanding Docker Compose Profiles**:

Docker Compose profiles (v1.28+) allow conditional service enabling.

**Example Usage**:

```yaml
# docker-compose.yml
services:
  open-webui:
    profiles:
      - ${OPENWEBUI_PROFILE:-default}
```

**Behavior**:
- If `OPENWEBUI_PROFILE` is empty or "default": service starts
- If `OPENWEBUI_PROFILE=disabled`: service doesn't start

**Commands**:
```bash
# Start all services (including Open WebUI if profile = default)
docker compose up -d

# Explicitly start Open WebUI (regardless of profile)
docker compose --profile default up -d open-webui

# Start everything except Open WebUI
export OPENWEBUI_PROFILE=disabled
docker compose up -d
```

### Appendix D: Docker Hub Mirror Verification Checklist

**Use this checklist on Day 1 of implementation**:

- [ ] Step 1: Identify candidate mirrors
  - [ ] Search Docker Hub: `docker search open-webui`
  - [ ] Check Open WebUI documentation for official mirrors
  - [ ] List 3-5 candidates with most pulls/stars

- [ ] Step 2: Check maintainer reputation
  - [ ] Verified publisher badge?
  - [ ] Organization account or personal?
  - [ ] Other images published (quality check)
  - [ ] GitHub profile linked?

- [ ] Step 3: Verify image integrity
  - [ ] Pull both GHCR and Docker Hub images
  - [ ] Compare image sizes (should be within 10%)
  - [ ] Extract and compare layer hashes
  - [ ] Check image creation dates (should be recent)

- [ ] Step 4: Security scan
  - [ ] Run Trivy/Clair/Snyk on both images
  - [ ] Compare vulnerability counts
  - [ ] Investigate any extra vulnerabilities in mirror

- [ ] Step 5: Functional testing
  - [ ] Run mirror image in isolation
  - [ ] Verify UI loads correctly
  - [ ] Test Ollama connection
  - [ ] Send test message and verify response
  - [ ] Monitor network traffic (no unexpected connections)

- [ ] Step 6: Community verification
  - [ ] Search for mentions on GitHub issues
  - [ ] Check Reddit/Discord for community trust
  - [ ] Contact Open WebUI maintainers for confirmation

- [ ] Step 7: Document decision
  - [ ] Create `docs/security/mirror-verification.md`
  - [ ] List verified mirror (or "none found")
  - [ ] Include verification evidence
  - [ ] Sign off by security reviewer

**Decision**:
- [ ] ✅ Use Docker Hub mirror: `docker.io/_______________`
- [ ] ❌ No trustworthy mirror found, use build-from-source
- [ ] ⏸️ Investigation incomplete, delay implementation

### Appendix E: Quick Reference Commands

**Setup**:
```bash
# Fresh installation
./scripts/setup/first_run.sh  # Linux/Mac
powershell -ExecutionPolicy Bypass -File .\scripts\setup\first_run.ps1  # Windows

# With Open WebUI disabled
echo "OPENWEBUI_PROFILE=disabled" >> .env
./scripts/setup/first_run.sh
```

**Service Management**:
```bash
cd infra

# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart Open WebUI only
docker compose restart open-webui

# View logs
docker compose logs -f open-webui

# Remove Open WebUI (keep data)
docker compose stop open-webui
docker compose rm open-webui

# Remove Open WebUI (delete data)
docker compose down -v open-webui
```

**Troubleshooting**:
```bash
# Check if Open WebUI is running
docker ps | grep openwebui

# Check Open WebUI health
curl http://localhost:3000

# Check Ollama connection from Open WebUI
docker exec maestro-openwebui curl http://host.docker.internal:11434/api/tags

# Pull image manually
docker pull ghcr.io/open-webui/open-webui:latest

# Authenticate with GHCR
docker login ghcr.io
# Username: your-github-username
# Password: your-github-PAT
```

**Testing**:
```bash
# Run fresh install test
cd /tmp
git clone https://github.com/lordmuffin/Maestro.git maestro-test
cd maestro-test
./scripts/setup/first_run.sh

# Cleanup test installation
cd /tmp
docker compose -f maestro-test/infra/docker-compose.yml down -v
rm -rf maestro-test
```

---

## Approval & Sign-Off

**Plan Author**: [Your Name]
**Date Created**: 2025-01-11
**Plan Version**: 1.0

**Approvals Required**:
- [ ] Project Lead: _________________ Date: _______
- [ ] Technical Lead: _________________ Date: _______
- [ ] Security Reviewer: _________________ Date: _______
- [ ] Community Representative: _________________ Date: _______

**Implementation Start Date**: _______________
**Target Release Date**: _______________

**Notes**:
[Space for reviewer comments and conditions]

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-11 | [Your Name] | Initial plan created |
| | | | |

---

**End of Implementation Plan**
