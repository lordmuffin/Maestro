#!/bin/bash
# First-time setup script for Maestro

set -e

echo "=== Maestro: First-Time Setup ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and configure your settings before continuing"
    echo "At minimum, set secure values for:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - JWT_SECRET"
    echo "  - WEBUI_SECRET_KEY"
    echo ""
    echo "To use your existing Obsidian vault:"
    echo "  - LOCAL_OBSIDIAN_PATH (path to your Obsidian vault directory)"
    echo ""
    echo "For Google Drive API integration (optional), also configure:"
    echo "  - GOOGLE_CLOUD_PROJECT"
    echo "  - GOOGLE_APPLICATION_CREDENTIALS"
    echo "  - GOOGLE_DRIVE_FOLDER_ID"
    echo "  - GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY"
    exit 1
fi

# Load environment variables
source .env

# Create necessary directories based on configuration
echo "Setting up directories..."

# Handle Obsidian vault path
if [ -n "$LOCAL_OBSIDIAN_PATH" ]; then
    echo "✓ Using local Obsidian vault at: $LOCAL_OBSIDIAN_PATH"
    if [ ! -d "$LOCAL_OBSIDIAN_PATH" ]; then
        echo "⚠️  Warning: LOCAL_OBSIDIAN_PATH does not exist: $LOCAL_OBSIDIAN_PATH"
        echo "   Please create this directory or update LOCAL_OBSIDIAN_PATH in .env"
    fi
else
    echo "Creating default data directories..."
    mkdir -p data/vault
    echo "✓ Default vault directory created at ./data/vault"
fi

# Create storage directory
mkdir -p data/storage

# Create gdrive-sync directory if Google Drive API is configured
if [ -n "$GOOGLE_DRIVE_FOLDER_ID" ] && [ "$GOOGLE_DRIVE_FOLDER_ID" != "your-drive-folder-id" ]; then
    echo "Google Drive API integration detected..."
    mkdir -p data/gdrive-sync
    echo "✓ Google Drive sync directory created at ./data/gdrive-sync"
fi

# Validate Google Drive API credentials if configured
if [ -n "$GOOGLE_DRIVE_FOLDER_ID" ] && [ "$GOOGLE_DRIVE_FOLDER_ID" != "your-drive-folder-id" ]; then
    # Check for Google credentials file
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        CREDS_FILE="${GOOGLE_APPLICATION_CREDENTIALS#/app/}"
        if [ ! -f "$CREDS_FILE" ]; then
            echo "⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS set but file not found: $CREDS_FILE"
            echo "   Please place your Google Cloud credentials JSON file at: $CREDS_FILE"
        else
            echo "✓ Google Cloud credentials file found"
        fi
    fi

    # Validate required Google Drive environment variables
    if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id" ]; then
        echo "⚠️  Warning: GOOGLE_CLOUD_PROJECT not configured in .env"
    fi

    if [ -z "$GOOGLE_API_KEY" ] && [ -z "$GOOGLE_GEMINI_API_KEY" ]; then
        echo "⚠️  Warning: Neither GOOGLE_API_KEY nor GOOGLE_GEMINI_API_KEY configured in .env"
    fi
fi

mkdir -p credentials

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Please install Docker and docker-compose."
    exit 1
fi

# Function to try pulling Open WebUI image with fallback
try_pull_openwebui() {
  local primary_image="ghcr.io/open-webui/open-webui:main"
  local fallback_image="backplane/open-webui:main"

  # Check if Open WebUI is explicitly disabled
  if grep -q "^OPENWEBUI_ENABLED=false" .env 2>/dev/null; then
    echo "ℹ️  Open WebUI is disabled (OPENWEBUI_ENABLED=false)"
    echo "   Skipping Open WebUI image pull"

    # Set profile to disabled if not already set
    if ! grep -q "^OPENWEBUI_PROFILE=" .env 2>/dev/null; then
      echo "OPENWEBUI_PROFILE=disabled" >> .env
    fi

    return 0
  fi

  echo ""
  echo "===================================="
  echo "Pulling Open WebUI Image"
  echo "===================================="
  echo "📦 Attempting to pull: $primary_image"
  echo ""

  # Try primary (GHCR)
  if docker pull "$primary_image" 2>/dev/null; then
    echo "✅ Successfully pulled from GitHub Container Registry"
    return 0
  fi

  echo "⚠️  Failed to pull from GHCR (authentication may be required)"
  echo ""
  echo "🔄 Trying fallback mirror: $fallback_image"
  echo "   (Unofficial automated mirror from Docker Hub)"

  # Try fallback (Docker Hub mirror)
  if docker pull "$fallback_image" 2>/dev/null; then
    echo "✅ Successfully pulled from Docker Hub mirror"
    echo ""
    echo "ℹ️  Note: Using community-maintained mirror (backplane/open-webui)"
    echo "   This is an automated daily sync from the official GHCR repository"
    echo "   To use official image, authenticate with GHCR:"
    echo "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
    echo ""

    # Tag fallback as primary image so docker-compose uses it
    docker tag "$fallback_image" "$primary_image"
    return 0
  fi

  echo "❌ Failed to pull from Docker Hub mirror"
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "⚠️  WARNING: Could not automatically pull Open WebUI image"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
  echo "Options to resolve:"
  echo ""
  echo "1. Authenticate with GitHub Container Registry (RECOMMENDED):"
  echo "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
  echo "   (Use a GitHub Personal Access Token with 'read:packages' scope)"
  echo "   Then run this script again"
  echo ""
  echo "2. Continue without Open WebUI (use API only):"
  echo "   Add 'OPENWEBUI_ENABLED=false' to your .env file"
  echo ""
  echo "3. Manual pull and retry:"
  echo "   Try pulling manually, then run this script again"
  echo ""

  # Ask user if they want to continue without Open WebUI
  read -p "Continue setup without Open WebUI? (Y/n): " response
  if [[ "$response" =~ ^[Nn]$ ]]; then
    echo ""
    echo "Setup cancelled. Please resolve the image issue and try again."
    echo "See documentation for detailed troubleshooting."
    exit 1
  fi

  echo ""
  echo "⚠️  Continuing without Open WebUI..."
  echo "   Adding OPENWEBUI_ENABLED=false to .env"
  echo ""
  echo "OPENWEBUI_ENABLED=false" >> .env
  echo "OPENWEBUI_PROFILE=disabled" >> .env
  return 0
}

# Navigate to infra directory
cd infra

# Try to pull Open WebUI with fallback logic
cd ..
try_pull_openwebui
cd infra

# Start containers
echo ""
echo "===================================="
echo "Starting Docker Containers"
echo "===================================="
docker-compose up -d

# Wait for services
echo ""
echo "Waiting for services to be ready..."
sleep 15

echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
if [ -n "$LOCAL_OBSIDIAN_PATH" ]; then
    echo "1. Obsidian vault configured at: $LOCAL_OBSIDIAN_PATH"
else
    echo "1. Place your Obsidian vault in ./data/vault/"
    echo "   Or set LOCAL_OBSIDIAN_PATH in .env to use an existing vault"
fi
echo "2. Access Open WebUI at http://localhost:3000"
echo "3. Access API docs at http://localhost:8000/docs"
echo "4. Check health status at http://localhost:8000/health"
echo ""
echo "To stop: cd infra && docker-compose down"
echo "To view logs: cd infra && docker-compose logs -f"
