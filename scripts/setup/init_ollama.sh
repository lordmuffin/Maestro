#!/bin/bash
# Initialize Ollama and pull required models

set -e

echo "=== Maestro: Ollama Initialization ==="

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
until curl -f http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
    echo "Still waiting..."
done

echo "Ollama is ready!"

# Pull default model
MODEL="${OLLAMA_MODEL:-llama3:8b}"
echo "Pulling model: $MODEL"
docker exec maestro-ollama ollama pull $MODEL

echo "Model pulled successfully!"

# List available models
echo "Available models:"
docker exec maestro-ollama ollama list

echo "=== Ollama initialization complete ==="
