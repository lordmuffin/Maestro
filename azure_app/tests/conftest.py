import pytest
from unittest.mock import MagicMock, patch
import os
import json

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
    monkeypatch.setenv("COSMOS_DB_ENDPOINT", "https://test.documents.azure.com:443/")
    monkeypatch.setenv("COSMOS_DB_KEY", "test_key")
    monkeypatch.setenv("FUNCTION_URL", "http://localhost")

@pytest.fixture
def mock_cosmos(mocker):
    mock_client = mocker.patch("azure_app.function_app.CosmosClient")
    mock_db = mock_client.return_value.get_database_client.return_value
    mock_container = mock_db.get_container_client.return_value
    return mock_container

@pytest.fixture
def mock_gemini(mocker):
    mock_genai = mocker.patch("azure_app.function_app.genai")
    mock_model = mock_genai.GenerativeModel.return_value
    return mock_model
