#!/usr/bin/env pwsh
# First-time setup script for Maestro

$ErrorActionPreference = "Stop"

Write-Host "=== Maestro: First-Time Setup ===" -ForegroundColor Cyan

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit .env and configure your settings before continuing" -ForegroundColor Yellow
    Write-Host "At minimum, set secure values for:"
    Write-Host "  - POSTGRES_PASSWORD"
    Write-Host "  - JWT_SECRET"
    Write-Host "  - WEBUI_SECRET_KEY"
    Write-Host ""
    Write-Host "To use your existing Obsidian vault:"
    Write-Host "  - LOCAL_OBSIDIAN_PATH (path to your Obsidian vault directory)"
    Write-Host ""
    Write-Host "For Google Drive API integration (optional), also configure:"
    Write-Host "  - GOOGLE_CLOUD_PROJECT"
    Write-Host "  - GOOGLE_APPLICATION_CREDENTIALS"
    Write-Host "  - GOOGLE_DRIVE_FOLDER_ID"
    Write-Host "  - GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY"
    exit 1
}

# Load environment variables from .env file
Write-Host "Loading environment variables..." -ForegroundColor Cyan
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        # Remove quotes if present
        $value = $value -replace '^["'']|["'']$', ''
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

# Create necessary directories based on configuration
Write-Host "Setting up directories..." -ForegroundColor Cyan

# Handle Obsidian vault path
$localObsidianPath = $env:LOCAL_OBSIDIAN_PATH
if ($localObsidianPath) {
    Write-Host "✓ Using local Obsidian vault at: $localObsidianPath" -ForegroundColor Green
    if (-Not (Test-Path $localObsidianPath)) {
        Write-Host "⚠️  Warning: LOCAL_OBSIDIAN_PATH does not exist: $localObsidianPath" -ForegroundColor Yellow
        Write-Host "   Please create this directory or update LOCAL_OBSIDIAN_PATH in .env" -ForegroundColor Yellow
    }
} else {
    Write-Host "Creating default data directories..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path "data\vault" | Out-Null
    Write-Host "✓ Default vault directory created at .\data\vault" -ForegroundColor Green
}

# Create storage directory
New-Item -ItemType Directory -Force -Path "data\storage" | Out-Null

# Create gdrive-sync directory if Google Drive API is configured
$googleDriveFolderId = $env:GOOGLE_DRIVE_FOLDER_ID
if ($googleDriveFolderId -and $googleDriveFolderId -ne "your-drive-folder-id") {
    Write-Host "Google Drive API integration detected..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path "data\gdrive-sync" | Out-Null
    Write-Host "✓ Google Drive sync directory created at .\data\gdrive-sync" -ForegroundColor Green
}

# Validate Google Drive API credentials if configured
if ($googleDriveFolderId -and $googleDriveFolderId -ne "your-drive-folder-id") {
    # Check for Google credentials file
    $googleCredentials = $env:GOOGLE_APPLICATION_CREDENTIALS
    if ($googleCredentials) {
        $credsFile = $googleCredentials -replace '^/app/', ''
        if (-Not (Test-Path $credsFile)) {
            Write-Host "⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS set but file not found: $credsFile" -ForegroundColor Yellow
            Write-Host "   Please place your Google Cloud credentials JSON file at: $credsFile" -ForegroundColor Yellow
        } else {
            Write-Host "✓ Google Cloud credentials file found" -ForegroundColor Green
        }
    }

    # Validate required Google Drive environment variables
    $googleCloudProject = $env:GOOGLE_CLOUD_PROJECT
    if (-Not $googleCloudProject -or $googleCloudProject -eq "your-project-id") {
        Write-Host "⚠️  Warning: GOOGLE_CLOUD_PROJECT not configured in .env" -ForegroundColor Yellow
    }

    $googleApiKey = $env:GOOGLE_API_KEY
    $googleGeminiApiKey = $env:GOOGLE_GEMINI_API_KEY
    if (-Not $googleApiKey -and -Not $googleGeminiApiKey) {
        Write-Host "⚠️  Warning: Neither GOOGLE_API_KEY nor GOOGLE_GEMINI_API_KEY configured in .env" -ForegroundColor Yellow
    }
}

New-Item -ItemType Directory -Force -Path "credentials" | Out-Null

# Check if docker-compose or docker compose exists
$dockerComposeCmd = $null
if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
    $dockerComposeCmd = "docker-compose"
} elseif (Get-Command "docker" -ErrorAction SilentlyContinue) {
    # Test if docker compose (v2) works
    $testCompose = docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $dockerComposeCmd = "docker compose"
    }
}

if (-Not $dockerComposeCmd) {
    Write-Host "Error: docker-compose or docker compose not found. Please install Docker and Docker Compose." -ForegroundColor Red
    exit 1
}

# Function to try pulling Open WebUI image with fallback
function Try-Pull-OpenWebUI {
    $primaryImage = "ghcr.io/open-webui/open-webui:main"
    $fallbackImage = "backplane/open-webui:main"

    # Check if Open WebUI is explicitly disabled
    if (Select-String -Path ".env" -Pattern "^OPENWEBUI_ENABLED=false" -Quiet) {
        Write-Host ""
        Write-Host "ℹ️  Open WebUI is disabled (OPENWEBUI_ENABLED=false)" -ForegroundColor Yellow
        Write-Host "   Skipping Open WebUI image pull"

        # Set profile to disabled if not already set
        if (-Not (Select-String -Path ".env" -Pattern "^OPENWEBUI_PROFILE=" -Quiet)) {
            Add-Content -Path ".env" -Value "OPENWEBUI_PROFILE=disabled"
        }

        return $true
    }

    Write-Host ""
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "Pulling Open WebUI Image" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "📦 Attempting to pull: $primaryImage"
    Write-Host ""

    # Try primary (GHCR)
    $ghcrResult = docker pull $primaryImage 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Successfully pulled from GitHub Container Registry" -ForegroundColor Green
        return $true
    }

    Write-Host "⚠️  Failed to pull from GHCR (authentication may be required)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔄 Trying fallback mirror: $fallbackImage" -ForegroundColor Cyan
    Write-Host "   (Unofficial automated mirror from Docker Hub)"

    # Try fallback (Docker Hub mirror)
    $fallbackResult = docker pull $fallbackImage 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Successfully pulled from Docker Hub mirror" -ForegroundColor Green
        Write-Host ""
        Write-Host "ℹ️  Note: Using community-maintained mirror (backplane/open-webui)" -ForegroundColor Yellow
        Write-Host "   This is an automated daily sync from the official GHCR repository"
        Write-Host "   To use official image, authenticate with GHCR:"
        Write-Host "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
        Write-Host ""

        # Tag fallback as primary image so docker-compose uses it
        docker tag $fallbackImage $primaryImage
        return $true
    }

    Write-Host "❌ Failed to pull from Docker Hub mirror" -ForegroundColor Red
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "⚠️  WARNING: Could not automatically pull Open WebUI image" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "Options to resolve:"
    Write-Host ""
    Write-Host "1. Authenticate with GitHub Container Registry (RECOMMENDED):"
    Write-Host "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
    Write-Host "   (Use a GitHub Personal Access Token with 'read:packages' scope)"
    Write-Host "   Then run this script again"
    Write-Host ""
    Write-Host "2. Continue without Open WebUI (use API only):"
    Write-Host "   Add 'OPENWEBUI_ENABLED=false' to your .env file"
    Write-Host ""
    Write-Host "3. Manual pull and retry:"
    Write-Host "   Try pulling manually, then run this script again"
    Write-Host ""

    # Ask user if they want to continue without Open WebUI
    $response = Read-Host "Continue setup without Open WebUI? (Y/n)"
    if ($response -match "^[Nn]$") {
        Write-Host ""
        Write-Host "Setup cancelled. Please resolve the image issue and try again." -ForegroundColor Yellow
        Write-Host "See documentation for detailed troubleshooting."
        exit 1
    }

    Write-Host ""
    Write-Host "⚠️  Continuing without Open WebUI..." -ForegroundColor Yellow
    Write-Host "   Adding OPENWEBUI_ENABLED=false to .env"
    Write-Host ""
    Add-Content -Path ".env" -Value "`nOPENWEBUI_ENABLED=false"
    Add-Content -Path ".env" -Value "OPENWEBUI_PROFILE=disabled"
    return $true
}

# Try to pull Open WebUI with fallback logic
Try-Pull-OpenWebUI | Out-Null

# Navigate to infra directory
Push-Location infra

try {
    # Start containers
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host "Starting Docker Containers" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    if ($dockerComposeCmd -eq "docker-compose") {
        docker-compose up -d
    } else {
        docker compose up -d
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start Docker containers"
    }

    # Wait for services
    Write-Host "Waiting for services to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15

    Write-Host ""
    Write-Host "=== Setup complete! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    if ($localObsidianPath) {
        Write-Host "1. Obsidian vault configured at: $localObsidianPath"
    } else {
        Write-Host "1. Place your Obsidian vault in .\data\vault\"
        Write-Host "   Or set LOCAL_OBSIDIAN_PATH in .env to use an existing vault"
    }
    Write-Host "2. Access Open WebUI at http://localhost:3000"
    Write-Host "3. Access API docs at http://localhost:8000/docs"
    Write-Host "4. Check health status at http://localhost:8000/health"
    Write-Host ""
    Write-Host "To stop: cd infra && docker-compose down (or docker compose down)"
    Write-Host "To view logs: cd infra && docker-compose logs -f (or docker compose logs -f)"
} finally {
    # Return to original directory
    Pop-Location
}
