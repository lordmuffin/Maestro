#!/usr/bin/env pwsh
# Initialize Ollama and pull required models

$ErrorActionPreference = "Stop"

Write-Host "=== Maestro: Ollama Initialization ===" -ForegroundColor Cyan

# Wait for Ollama to be ready
Write-Host "Waiting for Ollama to be ready..." -ForegroundColor Cyan
$maxAttempts = 60
$attempt = 0
$isReady = $false

while (-Not $isReady -and $attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $isReady = $true
            break
        }
    } catch {
        # Ollama not ready yet
    }

    Start-Sleep -Seconds 2
    $attempt++
    Write-Host "Still waiting..." -ForegroundColor Yellow
}

if (-Not $isReady) {
    Write-Host "Error: Ollama did not become ready in time." -ForegroundColor Red
    Write-Host "Please check if the Ollama container is running: docker ps" -ForegroundColor Yellow
    exit 1
}

Write-Host "Ollama is ready!" -ForegroundColor Green

# Pull default model
$model = $env:OLLAMA_MODEL
if (-Not $model) {
    $model = "llama3:8b"
}

Write-Host "Pulling model: $model" -ForegroundColor Cyan
docker exec maestro-ollama ollama pull $model

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to pull model $model" -ForegroundColor Red
    exit 1
}

Write-Host "Model pulled successfully!" -ForegroundColor Green

# List available models
Write-Host "Available models:" -ForegroundColor Cyan
docker exec maestro-ollama ollama list

Write-Host ""
Write-Host "=== Ollama initialization complete ===" -ForegroundColor Green
