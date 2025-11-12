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

# Navigate to infra directory
Push-Location infra

try {
    # Start containers
    Write-Host "Starting Docker containers..." -ForegroundColor Cyan
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
