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
    exit 1
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/vault
mkdir -p data/gdrive-sync
mkdir -p data/storage
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
