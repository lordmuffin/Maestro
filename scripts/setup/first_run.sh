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
    echo "For Google Drive integration (optional), also configure:"
    echo "  - GOOGLE_CLOUD_PROJECT"
    echo "  - GOOGLE_APPLICATION_CREDENTIALS"
    echo "  - GOOGLE_DRIVE_FOLDER_ID"
    echo "  - GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY"
    exit 1
fi

# Load environment variables
source .env

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/vault
mkdir -p data/storage

# Create Google Drive sync directory if Google Drive is configured
if [ -n "$GOOGLE_DRIVE_FOLDER_ID" ] && [ "$GOOGLE_DRIVE_FOLDER_ID" != "your-drive-folder-id" ]; then
    echo "Google Drive integration detected..."
    mkdir -p data/gdrive-sync

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

    echo "✓ Google Drive sync directory created"
else
    echo "Google Drive integration not configured (skipping gdrive-sync directory)"
fi

mkdir -p credentials

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Please install Docker and docker-compose."
    exit 1
fi

# Navigate to infra directory
cd infra

# Start containers
echo "Starting Docker containers..."
docker-compose up -d

# Wait for services
echo "Waiting for services to be ready..."
sleep 15

echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Place your Obsidian vault in ./data/vault/"
echo "2. Access Open WebUI at http://localhost:3000"
echo "3. Access API docs at http://localhost:8000/docs"
echo "4. Check health status at http://localhost:8000/health"
echo ""
echo "To stop: cd infra && docker-compose down"
echo "To view logs: cd infra && docker-compose logs -f"
