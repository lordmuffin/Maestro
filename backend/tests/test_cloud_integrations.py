"""Tests for cloud integration components."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from integrations.google.drive_client import GoogleDriveClient
from integrations.google.gemini_client import GeminiClient
from core.rag.cloud_rag import CloudRAG


class TestGoogleDriveClient:
    """Tests for Google Drive client."""

    @patch('integrations.google.drive_client.service_account')
    @patch('integrations.google.drive_client.build')
    def test_init(self, mock_build, mock_service_account):
        """Test Drive client initialization."""
        mock_service_account.Credentials.from_service_account_file.return_value = Mock()
        mock_build.return_value = Mock()

        client = GoogleDriveClient(credentials_path="/fake/path.json")

        assert client.service is not None
        mock_service_account.Credentials.from_service_account_file.assert_called_once()

    @patch('integrations.google.drive_client.service_account')
    @patch('integrations.google.drive_client.build')
    def test_list_files(self, mock_build, mock_service_account):
        """Test listing files."""
        # Setup mocks
        mock_service_account.Credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        mock_files = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {
            'files': [
                {'id': '1', 'name': 'test1.md'},
                {'id': '2', 'name': 'test2.md'}
            ]
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files

        # Test
        client = GoogleDriveClient(credentials_path="/fake/path.json")
        files = client.list_files(folder_id="test_folder")

        assert len(files) == 2
        assert files[0]['name'] == 'test1.md'

    @patch('integrations.google.drive_client.service_account')
    @patch('integrations.google.drive_client.build')
    def test_get_file_metadata(self, mock_build, mock_service_account):
        """Test getting file metadata."""
        # Setup mocks
        mock_service_account.Credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        mock_files = Mock()
        mock_get = Mock()
        mock_get.execute.return_value = {
            'id': 'test123',
            'name': 'test.md',
            'mimeType': 'text/markdown'
        }
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files

        # Test
        client = GoogleDriveClient(credentials_path="/fake/path.json")
        metadata = client.get_file_metadata('test123')

        assert metadata['id'] == 'test123'
        assert metadata['name'] == 'test.md'

    @patch('integrations.google.drive_client.service_account')
    @patch('integrations.google.drive_client.build')
    def test_search_files(self, mock_build, mock_service_account):
        """Test searching files."""
        # Setup mocks
        mock_service_account.Credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        mock_files = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {
            'files': [{'id': '1', 'name': 'matching.md'}]
        }
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files

        # Test
        client = GoogleDriveClient(credentials_path="/fake/path.json")
        results = client.search_files('test query')

        assert len(results) == 1
        assert results[0]['name'] == 'matching.md'


class TestGeminiClient:
    """Tests for Gemini client."""

    @patch('integrations.google.gemini_client.genai')
    def test_init_with_api_key(self, mock_genai):
        """Test Gemini client initialization with API key."""
        mock_genai.GenerativeModel.return_value = Mock()

        client = GeminiClient(api_key="test_key")

        assert client.model is not None
        mock_genai.configure.assert_called_once_with(api_key="test_key")

    @patch('integrations.google.gemini_client.genai')
    @patch('integrations.google.gemini_client.settings')
    def test_init_without_api_key(self, mock_settings, mock_genai):
        """Test Gemini client initialization without API key."""
        mock_settings.google_gemini_api_key = None

        client = GeminiClient()

        assert client.model is None

    @patch('integrations.google.gemini_client.genai')
    def test_generate(self, mock_genai):
        """Test text generation."""
        # Setup mock
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Generated response"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Test
        client = GeminiClient(api_key="test_key")
        response = client.generate("Test prompt")

        assert response == "Generated response"
        mock_model.generate_content.assert_called_once()

    @patch('integrations.google.gemini_client.genai')
    def test_chat(self, mock_genai):
        """Test chat conversation."""
        # Setup mock
        mock_model = Mock()
        mock_chat = Mock()
        mock_response = Mock()
        mock_response.text = "Chat response"
        mock_chat.send_message.return_value = mock_response
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model

        # Test
        client = GeminiClient(api_key="test_key")
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
        response = client.chat(messages)

        assert response == "Chat response"


class TestCloudRAG:
    """Tests for Cloud RAG system."""

    @patch('core.rag.cloud_rag.GoogleDriveClient')
    @patch('core.rag.cloud_rag.GeminiClient')
    def test_init(self, mock_gemini_cls, mock_drive_cls):
        """Test Cloud RAG initialization."""
        mock_drive_cls.return_value = Mock()
        mock_gemini_cls.return_value = Mock()

        cloud_rag = CloudRAG(
            credentials_path="/fake/creds.json",
            gemini_api_key="test_key"
        )

        assert cloud_rag.drive_client is not None
        assert cloud_rag.gemini_client is not None

    @patch('core.rag.cloud_rag.GoogleDriveClient')
    @patch('core.rag.cloud_rag.GeminiClient')
    def test_search_drive(self, mock_gemini_cls, mock_drive_cls):
        """Test Drive search."""
        # Setup mocks
        mock_drive = Mock()
        mock_drive.search_files.return_value = [
            {'id': '1', 'name': 'file1.md'},
            {'id': '2', 'name': 'file2.md'}
        ]
        mock_drive_cls.return_value = mock_drive
        mock_gemini_cls.return_value = Mock()

        # Test
        cloud_rag = CloudRAG(
            credentials_path="/fake/creds.json",
            gemini_api_key="test_key"
        )
        results = cloud_rag.search_drive("test query")

        assert len(results) == 2
        mock_drive.search_files.assert_called_once()

    @patch('core.rag.cloud_rag.GoogleDriveClient')
    @patch('core.rag.cloud_rag.GeminiClient')
    def test_query_with_context(self, mock_gemini_cls, mock_drive_cls):
        """Test query with file context."""
        # Setup mocks
        mock_drive = Mock()
        mock_drive.download_file_content.return_value = b"File content"
        mock_drive.get_file_metadata.return_value = {'name': 'test.md'}
        mock_drive_cls.return_value = mock_drive

        mock_gemini = Mock()
        mock_gemini.generate.return_value = "Generated answer"
        mock_gemini_cls.return_value = mock_gemini

        # Test
        cloud_rag = CloudRAG(
            credentials_path="/fake/creds.json",
            gemini_api_key="test_key"
        )
        result = cloud_rag.query_with_context(
            query="What is this about?",
            file_ids=["file1", "file2"]
        )

        assert result['response'] == "Generated answer"
        assert len(result['sources']) == 2
        assert result['query'] == "What is this about?"

    @patch('core.rag.cloud_rag.GoogleDriveClient')
    @patch('core.rag.cloud_rag.GeminiClient')
    def test_hybrid_search_no_results(self, mock_gemini_cls, mock_drive_cls):
        """Test hybrid search with no results."""
        # Setup mocks
        mock_drive = Mock()
        mock_drive.search_files.return_value = []
        mock_drive_cls.return_value = mock_drive
        mock_gemini_cls.return_value = Mock()

        # Test
        cloud_rag = CloudRAG(
            credentials_path="/fake/creds.json",
            gemini_api_key="test_key"
        )
        result = cloud_rag.hybrid_search("test query")

        assert "No relevant files found" in result['response']
        assert len(result['sources']) == 0
