import pytest
from azure_app.function_app import CosmosDBManager, GeminiClient, GitHubManager, get_prompt
import json

def test_cosmos_save_message(mock_cosmos):
    CosmosDBManager.save_message("session_1", "user", "hello")
    # Verify create_item or replace_item called
    # Since we mocked container, check calls
    assert mock_cosmos.read_item.called or mock_cosmos.create_item.called

def test_gemini_chat_response(mock_env, mock_gemini):
    # Mock the start_chat method on the model (mock_gemini is the model instance)
    mock_chat = mock_gemini.start_chat.return_value
    mock_chat.send_message.return_value.text = "AI Response"

    # We need to ensure ensure_genai_initialized doesn't fail or re-run badly
    # mock_env sets GOOGLE_API_KEY

    client = GeminiClient()
    response = client.chat_response("Hello", [])

    assert response == "AI Response"
    assert mock_gemini.start_chat.called

def test_get_prompt(monkeypatch):
    # Test fallback
    prompt = get_prompt("nonexistent.md")
    assert "helpful AI assistant" in prompt

def test_github_manager_init(mock_env):
    # Just test init for now as we mocked env
    manager = GitHubManager()
    assert manager
