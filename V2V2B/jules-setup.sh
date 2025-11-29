#!/bin/bash
# setup.sh for Google Jules - Maestro Project

set -e

echo "=== Setting up Maestro Environment ==="

# 1. Install System Dependencies
echo "Installing system libraries..."
sudo apt-get update
# Added 'curl' and 'gnupg' which are often required for the OpenTofu installer
sudo apt-get install -y git build-essential libpq-dev ffmpeg curl gnupg

# 2. Install OpenTofu (Latest Version)
echo "Installing OpenTofu..."
# Download the official installer script
curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh -o install-opentofu.sh
chmod +x install-opentofu.sh
# Run the installer with 'deb' method (safe for Debian/Ubuntu environments)
./install-opentofu.sh --install-method deb
rm install-opentofu.sh

# Verify OpenTofu installation
echo "Verifying OpenTofu version:"
tofu --version

# 3. Install Root Python Dependencies
# Found in requirements.txt (FastAPI, Anthropic, Gemini, etc.)
if [ -f "requirements.txt" ]; then
    echo "Installing root Python requirements..."
    pip install -r requirements.txt
fi

# 4. Install Backend Python Dependencies (Poetry)
# Found in backend/pyproject.toml (SQLAlchemy, Google Cloud libs, etc.)
if [ -d "backend" ] && [ -f "backend/pyproject.toml" ]; then
    echo "Installing backend dependencies via Poetry..."
    pip install poetry
    
    cd backend
    # Configure poetry to install in the system python environment for Jules visibility
    poetry config virtualenvs.create false
    poetry install --no-interaction --no-ansi
    cd ..
fi

# 5. Install Frontend Dependencies (Node.js)
# Found in maestro-ui/package.json (React, Vite, Tailwind)
if [ -d "maestro-ui" ] && [ -f "maestro-ui/package.json" ]; then
    echo "Installing frontend dependencies..."
    cd maestro-ui
    npm install
    cd ..
fi

# 6. Environment Configuration
# Create a .env file if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Generating .env from template..."
    cp .env.example .env
    # Set a dummy secret to pass basic validation checks during startup
    sed -i 's/generate-a-random-secret-key/dev-environment-secret-key/g' .env
fi

echo "=== Setup Complete ==="