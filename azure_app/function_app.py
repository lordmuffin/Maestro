"""
V2V2B Interrogator - Telegram Bot for Technical Content Extraction
Azure Functions Implementation
"""

import os
import logging
import json
import base64
import uuid
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
import requests
from io import BytesIO
from email.parser import BytesParser
from email.policy import default as email_default

import azure.functions as func
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import google.generativeai as genai
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
from googleapiclient.http import MediaInMemoryUpload

# Telegram Bot API
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Azure Function App
app = func.FunctionApp()

# Environment variables
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
REPO_NAME = os.environ.get('REPO_NAME')
FUNCTION_URL = os.environ.get('FUNCTION_URL')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')
OBSIDIAN_DRIVE_FOLDER_ID = os.environ.get('OBSIDIAN_DRIVE_FOLDER_ID', '')
KANBAN_FOLDER_ID = os.environ.get('KANBAN_FOLDER_ID', '')
BEYOND_REPO_NAME = os.environ.get('BEYOND_REPO_NAME', 'lordmuffin/beyond')
LOGS_WHITELIST = os.environ.get('LOGS_WHITELIST', '')
TARGET_FUNCTION_NAME = os.environ.get('TARGET_FUNCTION_NAME', 'v2v2b-interrogator')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
COSMOS_DB_ENDPOINT = os.environ.get('COSMOS_DB_ENDPOINT')
COSMOS_DB_KEY = os.environ.get('COSMOS_DB_KEY')
COSMOS_DB_DATABASE_NAME = os.environ.get('COSMOS_DB_DATABASE_NAME', 'v2v2b-db')
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON') # Content of JSON file

# Lazy initialization globals
_cosmos_client = None
_db_client = None
_genai_initialized = False
_prompts_cache = {}

# --- Database Manager (Cosmos DB) ---

class CosmosDBManager:
    """Manages Cosmos DB operations (replacing Firestore)."""

    @staticmethod
    def get_client():
        global _cosmos_client
        if _cosmos_client is None:
            if COSMOS_DB_KEY:
                _cosmos_client = CosmosClient(COSMOS_DB_ENDPOINT, credential=COSMOS_DB_KEY)
            else:
                # Fallback to Managed Identity
                _cosmos_client = CosmosClient(COSMOS_DB_ENDPOINT, credential=DefaultAzureCredential())
        return _cosmos_client

    @staticmethod
    def get_database():
        global _db_client
        if _db_client is None:
            client = CosmosDBManager.get_client()
            _db_client = client.get_database_client(COSMOS_DB_DATABASE_NAME)
        return _db_client

    @staticmethod
    def get_container(container_name: str):
        db = CosmosDBManager.get_database()
        return db.get_container_client(container_name)

    @staticmethod
    def save_message(session_id: str, role: str, content: str, space_name: str = None):
        """Save a message to session history."""
        try:
            container = CosmosDBManager.get_container('sessions')
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }

            try:
                item = container.read_item(item=session_id, partition_key=session_id)
                history = item.get('history', [])
                history.append(message)
                item['history'] = history
                item['last_updated'] = datetime.utcnow().isoformat()
                container.replace_item(item=session_id, body=item)
            except Exception: # Item not found
                item = {
                    'id': session_id,
                    'session_id': session_id,
                    'space_name': space_name,
                    'history': [message],
                    'created_at': datetime.utcnow().isoformat(),
                    'last_updated': datetime.utcnow().isoformat()
                }
                container.create_item(body=item)

            logger.info(f"Saved message to session {session_id}")
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    @staticmethod
    def get_session_history(session_id: str) -> List[Dict[str, str]]:
        """Retrieve session history."""
        try:
            container = CosmosDBManager.get_container('sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            return item.get('history', [])
        except Exception:
            return []

    @staticmethod
    def get_space_name(session_id: str) -> Optional[str]:
        try:
            container = CosmosDBManager.get_container('sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            return item.get('space_name')
        except Exception:
            return None

    @staticmethod
    def save_pending_validation(validation_id: str, session_id: str, chat_id: int,
                               file_type: str, filename: str, content: str,
                               structured_notes: str, file_data: bytes = None) -> None:
        try:
            container = CosmosDBManager.get_container('pending_validations')
            validation_data = {
                'id': validation_id,
                'validation_id': validation_id,
                'session_id': session_id,
                'chat_id': chat_id,
                'file_type': file_type,
                'filename': filename,
                'content': content,
                'structured_notes': structured_notes,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'awaiting_validation'
            }
            if file_data:
                validation_data['file_data_base64'] = base64.b64encode(file_data).decode('utf-8')

            container.upsert_item(body=validation_data)
            logger.info(f"Saved pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error saving pending validation: {e}")
            raise

    @staticmethod
    def get_pending_validation(validation_id: str) -> Optional[Dict[str, Any]]:
        try:
            container = CosmosDBManager.get_container('pending_validations')
            # Assuming partition key is id for simplicity in this migration
            return container.read_item(item=validation_id, partition_key=validation_id)
        except Exception:
            return None

    @staticmethod
    def delete_pending_validation(validation_id: str) -> None:
        try:
            container = CosmosDBManager.get_container('pending_validations')
            container.delete_item(item=validation_id, partition_key=validation_id)
            logger.info(f"Deleted pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error deleting pending validation: {e}")
            raise

    @staticmethod
    def create_interviewer_session(session_id: str, source_file_id: Optional[str],
                                   source_file_path: Optional[str], original_content: str) -> Dict[str, Any]:
        try:
            container = CosmosDBManager.get_container('interviewer_sessions')
            session_data = {
                'id': session_id,
                'session_id': session_id,
                'active': True,
                'completed': False,
                'source_file_id': source_file_id,
                'source_file_path': source_file_path,
                'original_content': original_content,
                'clarifications': [],
                'refined_notes': None,
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': None,
                'obsidian_path': None
            }
            container.upsert_item(body=session_data)
            logger.info(f"Created interviewer session {session_id}")
            return session_data
        except Exception as e:
            logger.error(f"Error creating interviewer session: {e}")
            raise

    @staticmethod
    def is_interviewer_active(session_id: str) -> bool:
        try:
            container = CosmosDBManager.get_container('interviewer_sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            return item.get('active', False) and not item.get('completed', False)
        except Exception:
            return False

    @staticmethod
    def get_interviewer_session(session_id: str) -> Optional[Dict[str, Any]]:
        try:
            container = CosmosDBManager.get_container('interviewer_sessions')
            return container.read_item(item=session_id, partition_key=session_id)
        except Exception:
            return None

    @staticmethod
    def add_clarification(session_id: str, question: str, answer: str) -> None:
        try:
            container = CosmosDBManager.get_container('interviewer_sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            clarifications = item.get('clarifications', [])
            clarifications.append({
                'question': question,
                'answer': answer,
                'timestamp': datetime.utcnow().isoformat()
            })
            item['clarifications'] = clarifications
            item['last_updated'] = datetime.utcnow().isoformat()
            container.replace_item(item=session_id, body=item)
            logger.info(f"Added clarification to session {session_id}")
        except Exception as e:
            logger.error(f"Error adding clarification: {e}")
            raise

    @staticmethod
    def complete_interviewer_session(session_id: str, refined_notes: str, obsidian_path: str) -> None:
        try:
            container = CosmosDBManager.get_container('interviewer_sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            item['active'] = False
            item['completed'] = True
            item['refined_notes'] = refined_notes
            item['obsidian_path'] = obsidian_path
            item['completed_at'] = datetime.utcnow().isoformat()
            container.replace_item(item=session_id, body=item)
            logger.info(f"Completed interviewer session {session_id}")
        except Exception as e:
            logger.error(f"Error completing interviewer session: {e}")
            raise

    @staticmethod
    def save_session_data(session_id: str, data: Dict[str, Any]):
        try:
            container = CosmosDBManager.get_container('sessions')
            try:
                item = container.read_item(item=session_id, partition_key=session_id)
                item['session_data'] = data
                container.replace_item(item=session_id, body=item)
            except Exception:
                item = {
                    'id': session_id,
                    'session_id': session_id,
                    'session_data': data,
                    'created_at': datetime.utcnow().isoformat()
                }
                container.create_item(body=item)
            logger.info(f"Saved session data for session {session_id}")
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
            raise

    @staticmethod
    def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
        try:
            container = CosmosDBManager.get_container('sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            return item.get('session_data')
        except Exception:
            return None

    @staticmethod
    def delete_session_data(session_id: str):
        try:
            container = CosmosDBManager.get_container('sessions')
            item = container.read_item(item=session_id, partition_key=session_id)
            if 'session_data' in item:
                del item['session_data']
                container.replace_item(item=session_id, body=item)
            logger.info(f"Deleted session data for session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session data: {e}")
            raise

# --- Prompt Loading ---

def load_prompt(prompt_filename: str) -> str:
    """Load a prompt from the prompts directory."""
    try:
        # Try finding prompts directory in potential locations
        # 1. Relative to function root (Azure deployment structure)
        # 2. Relative to file
        potential_paths = [
            Path(__file__).parent / "prompts",
            Path("prompts"),
            Path("azure_app/prompts"),
            Path("../prompts")
        ]

        prompt_content = None
        for base_path in potential_paths:
            prompt_path = base_path / prompt_filename
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                    logger.info(f"Loaded prompt from {prompt_path}")
                    break

        if prompt_content:
            return prompt_content
        else:
            logger.warning(f"Prompt file not found: {prompt_filename}. Using fallback.")
            return get_fallback_prompt(prompt_filename)

    except Exception as e:
        logger.error(f"Error loading prompt {prompt_filename}: {e}")
        return get_fallback_prompt(prompt_filename)

def get_fallback_prompt(prompt_filename: str) -> str:
    """Return fallback prompts if files cannot be loaded."""
    fallbacks = {
        "telegram_chat_prompt.md": """You are a professional technical interview assistant for the Maestro AI Executive Assistant.
Your goal is to extract valuable technical knowledge through respectful, focused conversation.
Be professional, curious, and methodical.""",
        "multimodal_analysis_prompt.md": """Analyze this audio or image content and extract meaningful information.
Provide structured insights including: key topics, technical concepts, action items, and areas needing clarification.
CRITICAL: If the image contains ambiguous text, output [CLARIFICATION_NEEDED] followed by your question.""",
        "transcript_analysis_prompt.md": """Analyze this transcript and extract key architectural concepts, decisions, and implementation details.""",
        "interrogation_questions_prompt.md": """Based on this analysis, generate a list of probing questions to extract more details.""",
        "interviewer_prompt.md": """# Role: Maestro Executive Interviewer
Analyze transcript for Action Items and Ambiguities. If ambiguous, ask clarifying questions.
When confirmed, format as Obsidian markdown with YAML frontmatter."""
    }
    return fallbacks.get(prompt_filename, "You are a helpful AI assistant.")

def get_prompt(prompt_name: str) -> str:
    """Lazy-load prompts with caching."""
    if prompt_name not in _prompts_cache:
        _prompts_cache[prompt_name] = load_prompt(prompt_name)
    return _prompts_cache[prompt_name]

# --- AI Client (Gemini via Google Generative AI SDK) ---

def ensure_genai_initialized():
    global _genai_initialized
    if not _genai_initialized:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=GOOGLE_API_KEY)
        _genai_initialized = True
        logger.info("Initialized Google Generative AI")

class GeminiClient:
    """Handles interactions with Google Gemini via API Key."""

    def __init__(self):
        ensure_genai_initialized()
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def chat_response(self, user_message: str, history: List[Dict[str, str]], session_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a chat response with context."""
        try:
            # Construct context
            system_prompt = get_prompt('telegram_chat_prompt.md')

            full_context = f"{system_prompt}\n"
            if session_data:
                full_context += f"\nSession Data:\n{json.dumps(session_data, indent=2)}\n"

            # Mapping history for start_chat
            genai_history = []

            # Start with system context
            genai_history.append({"role": "user", "parts": [full_context]})
            genai_history.append({"role": "model", "parts": ["Understood."]})

            for msg in history:
                role = "user" if msg['role'] == 'user' else "model"
                genai_history.append({"role": role, "parts": [msg['content']]})

            chat = self.model.start_chat(history=genai_history)
            response = chat.send_message(user_message)
            return response.text
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I seem to be experiencing technical difficulties. How ironic."

    def analyze_multimodal(self, file_data: bytes, mime_type: str, filename: str) -> str:
        """Analyze audio, image, video, or PDF file."""
        try:
            prompt_text = f"{get_prompt('multimodal_analysis_prompt.md')}\n\nFile: {filename}"
            if "[CLARIFICATION_NEEDED]" not in prompt_text:
                prompt_text += "\n\nCRITICAL: If the content is ambiguous, unclear, or cut-off, do NOT guess. Output [CLARIFICATION_NEEDED] followed by your question."

            content = [
                prompt_text,
                {
                    "mime_type": mime_type,
                    "data": file_data
                }
            ]

            response = self.model.generate_content(content)
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
            return f"Error analyzing file: {str(e)}"

# --- Helper Classes ---

def _setup_google_auth():
    """Setup Google Application Credentials from environment variable for Azure."""
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') and GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(GOOGLE_SERVICE_ACCOUNT_JSON)
                temp_path = f.name

            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_path
            logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS to {temp_path}")
        except Exception as e:
            logger.error(f"Failed to setup Google Auth: {e}")

class GoogleDriveClient:
    """Handles Google Drive operations."""
    def __init__(self):
        self._service = None
        _setup_google_auth() # Ensure auth is setup

    @property
    def service(self):
        if not self._service:
            credentials, _ = default()
            self._service = build('drive', 'v3', credentials=credentials)
        return self._service

    def list_files(self, folder_id: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
        try:
            if not folder_id: return []
            query = f"'{folder_id}' in parents and trashed=false"
            if file_types:
                mime_queries = []
                for ft in file_types:
                    if ft == '.txt': mime_queries.append("mimeType='text/plain'")
                    elif ft == '.m4a': mime_queries.append("mimeType='audio/x-m4a' or mimeType='audio/mp4'")
                if mime_queries: query += f" and ({' or '.join(mime_queries)})"

            results = self.service.files().list(
                q=query, fields="files(id, name, mimeType, createdTime, modifiedTime, size)",
                orderBy="createdTime desc", pageSize=100
            ).execute()
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return []

    def download_file(self, file_id: str) -> Optional[bytes]:
        try:
            metadata = self.get_file_metadata(file_id)
            if not metadata: return None
            mime_type = metadata.get('mimeType', '')
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            else:
                request = self.service.files().get_media(fileId=file_id)
            return request.execute()
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.service.files().get(
                fileId=file_id, fields="id, name, mimeType, createdTime, modifiedTime, size"
            ).execute()
        except Exception:
            return None

    def upload_file(self, folder_id: str, filename: str, content: str, mime_type: str = 'text/markdown') -> Optional[str]:
        try:
            file_metadata = {'name': filename, 'parents': [folder_id]}
            media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    def update_file_content(self, file_id: str, new_content: str) -> bool:
        try:
            metadata = self.get_file_metadata(file_id)
            mime_type = metadata.get('mimeType', 'text/plain') if metadata else 'text/plain'
            media = MediaInMemoryUpload(new_content.encode('utf-8'), mimetype=mime_type)
            self.service.files().update(fileId=file_id, media_body=media).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating file: {e}")
            return False

class RepositoryConfig:
    def __init__(self, name: str, label: str, token_env_var: str, description: str = "", paths: Dict[str, str] = None):
        self.name = name
        self.label = label
        self.token_env_var = token_env_var
        self.description = description
        self.paths = paths or {}
        self._token = None
        self._github_client = None
        self._repo = None

    @property
    def token(self):
        if self._token is None:
            self._token = os.environ.get(self.token_env_var)
            if not self._token: raise ValueError(f"Token not found for {self.token_env_var}")
        return self._token

    def get_github_client(self):
        if self._github_client is None: self._github_client = Github(self.token)
        return self._github_client

    def get_repo(self):
        if self._repo is None: self._repo = self.get_github_client().get_repo(self.name)
        return self._repo

class GitHubConfigManager:
    _instance = None
    def __init__(self, config_path: str = None):
        # Assuming repos.json is in same directory as function app
        if config_path is None: config_path = os.path.join(os.path.dirname(__file__), 'repos.json')
        self.config_path = config_path
        self.repositories = {}
        self.routing_rules = {}
        self.default_repo_label = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: str = None):
        if cls._instance is None: cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            for repo_data in data.get('repositories', []):
                label = repo_data['label']
                self.repositories[label] = RepositoryConfig(repo_data['name'], label, repo_data['token_env_var'], repo_data.get('description', ''), repo_data.get('paths', {}))
            self.default_repo_label = data.get('default_repository')
            self.routing_rules = data.get('routing_rules', {})
        except Exception as e:
            logger.error(f"Failed to load repo config: {e}")

    def get_repo_config(self, label: str = None, name: str = None) -> RepositoryConfig:
        if label: return self.repositories.get(label)
        if name:
            for repo in self.repositories.values():
                if repo.name == name: return repo
        return self.repositories[self.default_repo_label]

    def get_default_repo_for_operation(self, operation: str) -> RepositoryConfig:
        rule = self.routing_rules.get(operation)
        if rule and 'default_target' in rule: return self.get_repo_config(label=rule['default_target'])
        return self.get_repo_config()

class GitHubManager:
    def __init__(self, config_path: str = None):
        self.config_manager = GitHubConfigManager.get_instance(config_path)

    def _sanitize_git_ref_name(self, name: str, max_length: int = 50) -> str:
        # Simplistic sanitization
        import re
        safe = re.sub(r'[^a-zA-Z0-9-]', '-', name)
        return safe[:max_length]

    def _sanitize_filename(self, name: str, max_length: int = 150) -> str:
        import re
        safe = re.sub(r'[^a-zA-Z0-9-]', '-', name)
        return safe[:max_length]

    def _get_repo_for_operation(self, operation: str, repo_label: Optional[str] = None, repo_name: Optional[str] = None) -> RepositoryConfig:
        if repo_label or repo_name: return self.config_manager.get_repo_config(label=repo_label, name=repo_name)
        return self.config_manager.get_default_repo_for_operation(operation)

    def create_pr_from_session(self, session_id: str, history: List[Dict[str, str]], repo_label: str = None) -> str:
        repo_config = self._get_repo_for_operation('sessions', repo_label)
        repo = repo_config.get_repo()
        branch_name = f"session/{session_id.replace('@', '-').replace('.', '-')}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        default_branch = repo.default_branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch(default_branch).commit.sha)

        markdown = f"# Session: {session_id}\n\n"
        for msg in history: markdown += f"## {msg['role'].upper()}\n{msg['content']}\n\n"

        path = repo_config.paths.get('sessions', 'sessions/')
        filename = f"{path}{datetime.utcnow().strftime('%Y-%m-%d')}-{session_id.split('@')[0]}.md"
        repo.create_file(path=filename, message=f"Add session {session_id}", content=markdown, branch=branch_name)

        pr = repo.create_pull(title=f"Session: {session_id}", body="Automated PR", head=branch_name, base=default_branch)
        return pr.html_url

    def create_pr_from_transcript(self, filename: str, transcript: str, analysis: str, questions: str, metadata: Dict[str, Any]) -> str:
        repo_config = self._get_repo_for_operation('transcripts')
        repo = repo_config.get_repo()
        branch_name = f"transcript/{filename.replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        default_branch = repo.default_branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch(default_branch).commit.sha)

        content = f"# Analysis\n{analysis}\n\n# Questions\n{questions}\n\n# Transcript\n{transcript}"
        path = repo_config.paths.get('transcripts', 'transcripts/')
        file_path = f"{path}{datetime.now().strftime('%Y-%m-%d')}-{filename}.md"
        repo.create_file(path=file_path, message=f"Analysis: {filename}", content=content, branch=branch_name)

        pr = repo.create_pull(title=f"Transcript: {filename}", body=f"Analysis of {filename}", head=branch_name, base=default_branch)
        return pr.html_url

    def create_pr_from_interview(self, title: str, content: str, session_id: str, repo_label: str = 'beyond', target_path: str = None) -> str:
        repo_config = self._get_repo_for_operation('interviews', repo_label)
        repo = repo_config.get_repo()
        branch_name = f"interview/{title.replace(' ', '-')[:50]}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        default_branch = repo.default_branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch(default_branch).commit.sha)

        if target_path is None: target_path = repo_config.paths.get('interviews', '05_Maestro_Notes/')
        filename = f"{target_path}{datetime.now(timezone.utc).strftime('%Y-%m-%d')} - {title}.md"

        repo.create_file(path=filename, message=f"Interview: {title}", content=content, branch=branch_name)
        pr = repo.create_pull(title=f"Interview: {title}", body=f"Session: {session_id}", head=branch_name, base=default_branch)
        return pr.html_url

    def create_pr_from_session_data(self, session_id: str, summary: str, session_data: Dict[str, Any], repo_label: str = None) -> str:
        repo_config = self._get_repo_for_operation('sessions', repo_label)
        repo = repo_config.get_repo()
        branch_name = f"session/{session_id.replace('@', '-').replace('.', '-')}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        default_branch = repo.default_branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=repo.get_branch(default_branch).commit.sha)

        base_path = repo_config.paths.get('sessions', 'sessions/')
        session_folder = f"{base_path}{datetime.utcnow().strftime('%Y-%m-%d')}-{session_id.split('@')[0]}"

        repo.create_file(path=f"{session_folder}/session_data.json", message="Add session data", content=json.dumps(session_data, indent=2), branch=branch_name)
        repo.create_file(path=f"{session_folder}/summary.md", message="Add summary", content=summary, branch=branch_name)

        pr = repo.create_pull(title=f"Session Data: {session_id}", body="Automated PR", head=branch_name, base=default_branch)
        return pr.html_url

class KanbanManager:
    def __init__(self, drive_client: GoogleDriveClient):
        self.drive_client = drive_client
        self._kanban_file_id = None
        self._kanban_folder_id = None

    def find_kanban_file(self, folder_id: str, filename: str = "Personal Kanban.md") -> Optional[str]:
        if self._kanban_file_id: return self._kanban_file_id
        files = self.drive_client.list_files(folder_id)
        for f in files:
            if f['name'] == filename:
                self._kanban_file_id = f['id']
                return f['id']
        return None

    def extract_action_items(self, note_content: str, note_title: str) -> List[Dict[str, str]]:
        import re
        items = []
        match = re.search(r'## Action Items\s*\n(.*?)(?=\n##|\Z)', note_content, re.DOTALL)
        if match:
            for item_match in re.finditer(r'-\s*\[\s*\]\s*(.+?)\s*-\s*\*\*Owner:\*\*\s*\[\[(.+?)\]\](?:\s*-\s*\*\*Due:\*\*\s*(.+?))?', match.group(1)):
                items.append({
                    'task': item_match.group(1).strip(),
                    'owner': item_match.group(2).strip(),
                    'due_date': item_match.group(3).strip() if item_match.group(3) else "TBD",
                    'source_note': note_title
                })
        return items

    def update_kanban_board(self, action_items: List[Dict[str, str]], source_note_title: str) -> bool:
        if not action_items or not self._kanban_folder_id: return False
        file_id = self.find_kanban_file(self._kanban_folder_id)
        if not file_id: return False

        content_bytes = self.drive_client.download_file(file_id)
        if not content_bytes: return False
        content = content_bytes.decode('utf-8')

        new_tasks = []
        for item in action_items:
            new_tasks.append(f"- [ ] #Maestro **Task:** {item['task']} - Owner: [[{item['owner']}]] - Due: {item['due_date']}\n  - Source: [[{source_note_title}]]")

        # Simple append to "New" section or end of file
        if "## New" in content:
            content = content.replace("## New", "## New\n\n" + "\n\n".join(new_tasks))
        else:
            content += "\n\n## New\n\n" + "\n\n".join(new_tasks)

        return self.drive_client.update_file_content(file_id, content)

class ObsidianSync:
    def __init__(self, drive_client: GoogleDriveClient):
        self.drive_client = drive_client

    def sync_to_obsidian(self, filename: str, content: str, summary: str, tags: List[str], metadata: Dict[str, Any]) -> Optional[str]:
        if not OBSIDIAN_DRIVE_FOLDER_ID: return None
        base_name = filename.rsplit('.', 1)[0]
        md_filename = f"{base_name}.md"
        frontmatter = f"---\ntitle: {base_name}\ncreated: {metadata.get('createdTime')}\n---\n\n"
        full_content = f"{frontmatter}# {base_name}\n\n## Summary\n{summary}\n\n## Content\n{content}"
        return self.drive_client.upload_file(OBSIDIAN_DRIVE_FOLDER_ID, md_filename, full_content, 'text/markdown')

class TranscriptProcessor:
    def __init__(self, gemini_client):
        self.gemini = gemini_client

    def process_text_transcript(self, text: str) -> str: return text
    def process_audio_transcript(self, data: bytes, filename: str) -> str:
        return self.gemini.analyze_multimodal(data, "audio/mp4", filename)
    def analyze_transcript(self, text: str) -> str:
        return self.gemini.chat_response(f"Analyze this transcript:\n{text}", [])
    def generate_interrogation_questions(self, analysis: str) -> str:
        return self.gemini.chat_response(f"Generate interrogation questions based on:\n{analysis}", [])

class SyncTelegramClient:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
    def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode: str = 'Markdown') -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text}
        if parse_mode: payload['parse_mode'] = parse_mode
        if reply_markup: payload['reply_markup'] = reply_markup.to_json()
        try:
            requests.post(url, json=payload, timeout=10)
            return True
        except: return False

# --- Telegram Handlers ---

class BotHandlers:
    def __init__(self):
        self.gemini = GeminiClient()
        self.github_manager = GitHubManager()
        self.drive_client = GoogleDriveClient()
        self.kanban_manager = KanbanManager(self.drive_client)
        self.kanban_manager._kanban_folder_id = KANBAN_FOLDER_ID

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Hello! I'm the V2V2B Interrogator on Azure. Send me a message or file to start.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Commands: /start, /upload, /logs, /done, /help")

    async def upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        upload_url = f"{FUNCTION_URL}?mode=ui&session={session_id}"
        await update.message.reply_text(f"Upload files here: {upload_url}")

    async def done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()

        # Check if interview is active
        is_active = await loop.run_in_executor(None, CosmosDBManager.is_interviewer_active, session_id)
        if is_active:
            await self._handle_interview_complete(update, context, session_id)
        else:
            # Create PR for session history
            history = await loop.run_in_executor(None, CosmosDBManager.get_session_history, session_id)
            if history:
                pr_url = await loop.run_in_executor(None, self.github_manager.create_pr_from_session, session_id, history)
                await update.message.reply_text(f"Session saved! PR: {pr_url}")
            else:
                await update.message.reply_text("No session history to save.")

    async def _handle_interview_complete(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str):
        await update.message.reply_text('⏳ Finalizing your notes...')
        loop = asyncio.get_running_loop()

        try:
            session = await loop.run_in_executor(None, CosmosDBManager.get_interviewer_session, session_id)
            if not session:
                await update.message.reply_text('❌ No active interview session found.')
                return

            # Build context
            clarifications = session.get('clarifications', [])
            clarification_text = "\n\n".join([f"**Q:** {c['question']}\n**A:** {c['answer']}" for c in clarifications])

            interviewer_prompt = get_prompt("interviewer_prompt.md")
            finalization_msg = f"{interviewer_prompt}\n\n**ORIGINAL TRANSCRIPT:**\n{session['original_content']}\n\n**CLARIFICATIONS:**\n{clarification_text}\n\nPROCEED TO PHASE 3: FINALIZATION."

            history = await loop.run_in_executor(None, CosmosDBManager.get_session_history, session_id)
            final_notes = await loop.run_in_executor(None, self.gemini.chat_response, finalization_msg, history)

            # Extract title
            title = self._extract_title(final_notes)

            # Save to Obsidian
            new_file_name = None
            try:
                obsidian_sync = ObsidianSync(self.drive_client)
                # We need a synchronous wrapper or just call the sync method in executor
                def save_obsidian():
                    return obsidian_sync.sync_to_obsidian(
                        filename=f"{title}.md",
                        content=final_notes,
                        summary="Generated by Maestro",
                        tags=['Maestro', 'Interview'],
                        metadata={'createdTime': datetime.utcnow().isoformat()}
                    )
                file_id = await loop.run_in_executor(None, save_obsidian)
                if file_id: new_file_name = f"{title}.md"
            except Exception as e:
                logger.error(f"Obsidian save failed: {e}")

            # Create PR
            pr_url = None
            try:
                pr_url = await loop.run_in_executor(None, self.github_manager.create_pr_from_interview, title, final_notes, session_id)
                await update.message.reply_text(f"📝 PR created in beyond repository:\n{pr_url}")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Failed to create PR: {e}")

            # Complete session
            await loop.run_in_executor(None, CosmosDBManager.complete_interviewer_session, session_id, final_notes, str(new_file_name))
            await update.message.reply_text("✅ Interview Complete! Notes finalized.")

        except Exception as e:
            logger.error(f"Interview completion failed: {e}")
            await update.message.reply_text(f"❌ Error finalizing interview: {e}")

    def _extract_title(self, text: str) -> str:
        import re
        match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else f"Interview {datetime.utcnow().strftime('%Y-%m-%d')}"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return
        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        text = update.message.text

        loop = asyncio.get_running_loop()

        # Save user message
        await loop.run_in_executor(None, CosmosDBManager.save_message, session_id, 'user', text, str(update.effective_chat.id))

        # Get history
        history = await loop.run_in_executor(None, CosmosDBManager.get_session_history, session_id)

        # Generate response
        response = await loop.run_in_executor(None, self.gemini.chat_response, text, history)

        # Save and send response
        await loop.run_in_executor(None, CosmosDBManager.save_message, session_id, 'model', response, str(update.effective_chat.id))
        await update.message.reply_text(response)

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()

        try:
            # Determine file type
            file_obj = None
            filename = "unknown"
            mime_type = ""

            if message.document:
                file_obj = await message.document.get_file()
                filename = message.document.file_name or "document"
                mime_type = message.document.mime_type
            elif message.voice:
                file_obj = await message.voice.get_file()
                filename = f"voice_{datetime.now().strftime('%H%M%S')}.ogg"
                mime_type = "audio/ogg"
            elif message.audio:
                file_obj = await message.audio.get_file()
                filename = message.audio.file_name or "audio"
                mime_type = message.audio.mime_type
            elif message.video:
                file_obj = await message.video.get_file()
                filename = message.video.file_name or "video.mp4"
                mime_type = message.video.mime_type or "video/mp4"
            else:
                await update.message.reply_text("❌ Unsupported file type.")
                return

            await update.message.reply_text(f"📄 Processing {filename}...")

            # Download file
            byte_array = await file_obj.download_as_bytearray()
            file_data = bytes(byte_array)

            # Analyze based on type
            analysis = ""
            if mime_type == 'application/pdf' or filename.endswith('.pdf'):
                # Analyze PDF
                analysis = await loop.run_in_executor(None, self.gemini.analyze_multimodal, file_data, 'application/pdf', filename)
            elif mime_type.startswith('audio') or filename.endswith(('.ogg', '.m4a', '.mp3')):
                # Use audio type
                ctype = mime_type if mime_type else 'audio/mp4'
                analysis = await loop.run_in_executor(None, self.gemini.analyze_multimodal, file_data, ctype, filename)
            elif mime_type.startswith('video'):
                analysis = await loop.run_in_executor(None, self.gemini.analyze_multimodal, file_data, mime_type, filename)
            elif mime_type == 'text/plain' or filename.endswith(('.txt', '.md')):
                analysis = file_data.decode('utf-8', errors='ignore')
            else:
                await update.message.reply_text("❌ Unsupported format.")
                return

            # Start Interviewer Session
            await loop.run_in_executor(None, CosmosDBManager.create_interviewer_session, session_id, None, None, analysis)

            # Generate initial questions
            prompt = f"{get_prompt('interviewer_prompt.md')}\n\nTRANSCRIPT:\n{analysis}"
            questions = await loop.run_in_executor(None, self.gemini.chat_response, prompt, [])

            await loop.run_in_executor(None, CosmosDBManager.save_message, session_id, 'assistant', questions, str(update.effective_chat.id))

            await update.message.reply_text(f"📝 Analysis Complete. Starting interview:\n\n{questions}")

        except Exception as e:
            logger.error(f"File handler error: {e}")
            await update.message.reply_text(f"❌ Error processing file: {e}")

def init_bot() -> Application:
    if not TELEGRAM_BOT_TOKEN: raise ValueError("TELEGRAM_BOT_TOKEN not set")
    handlers = BotHandlers()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help))
    app.add_handler(CommandHandler("upload", handlers.upload))
    app.add_handler(CommandHandler("done", handlers.done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(MessageHandler(filters.ATTACHMENT | filters.VOICE, handlers.handle_file))
    return app

class UploadHandler:
    def __init__(self):
        self.gemini = GeminiClient()
        self.telegram_client = SyncTelegramClient()

    def handle(self, session_id: str, file_data: bytes, filename: str, content_type: str) -> str:
        try:
            analysis = self.gemini.analyze_multimodal(file_data, content_type, filename)
            CosmosDBManager.save_message(session_id, 'model', f"[FILE: {filename}]\n{analysis}")

            chat_id = CosmosDBManager.get_space_name(session_id)
            if chat_id: self.telegram_client.send_message(int(chat_id), f"File analyzed: {filename}\n{analysis}")

            return "<html><body>Upload Successful</body></html>"
        except Exception as e:
            return f"<html><body>Error: {e}</body></html>"

# --- Azure Function Entry Points ---

@app.route(route="telegram", auth_level=func.AuthLevel.ANONYMOUS)
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    try:
        update_data = req.get_json()
        if not update_data: return func.HttpResponse("Invalid body", status_code=400)

        async def process():
            bot_app = init_bot()
            await bot_app.initialize()
            await bot_app.process_update(Update.de_json(update_data, bot_app.bot))
            await bot_app.shutdown()

        asyncio.run(process())
        return func.HttpResponse(json.dumps({'status': 'ok'}), mimetype='application/json')
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return func.HttpResponse(json.dumps({'error': str(e)}), status_code=500)

@app.route(route="upload_ui", auth_level=func.AuthLevel.ANONYMOUS)
def upload_ui(req: func.HttpRequest) -> func.HttpResponse:
    session_id = req.params.get('session')
    if not session_id: return func.HttpResponse("Missing session", status_code=400)
    html = get_upload_ui_html(session_id)
    return func.HttpResponse(html, mimetype='text/html')

@app.route(route="upload_file", methods=['POST'], auth_level=func.AuthLevel.ANONYMOUS)
def upload_file_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        session_id = req.params.get('session')
        if not session_id: return func.HttpResponse("Missing session ID", status_code=400)

        content_type = req.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
             return func.HttpResponse("Invalid Content-Type", status_code=400)

        # Parse multipart body using standard email library
        # This avoids issues with external libraries like python-multipart in this context

        # 1. Prepend headers to make it look like an email message
        body_bytes = req.get_body()
        headers = f"Content-Type: {content_type}\r\n".encode('utf-8')
        msg_bytes = headers + b"\r\n" + body_bytes

        # 2. Parse using BytesParser
        parser = BytesParser(policy=email_default)
        msg = parser.parsebytes(msg_bytes)

        file_data = None
        filename = "uploaded_file"
        file_ctype = "application/octet-stream"

        # 3. Iterate parts to find the file
        if msg.is_multipart():
            for part in msg.iter_parts():
                # Check Content-Disposition
                disposition = part.get_content_disposition()
                if disposition == 'form-data':
                    # Check if it's the file field (usually named 'file') or has a filename
                    part_filename = part.get_filename()
                    if part_filename:
                        filename = part_filename
                        file_ctype = part.get_content_type()
                        file_data = part.get_payload(decode=True)
                        break

        if file_data:
            handler = UploadHandler()
            result = handler.handle(session_id, file_data, filename, file_ctype)
            return func.HttpResponse(result, mimetype='text/html')

        return func.HttpResponse("No file data received", status_code=400)
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)

def get_upload_ui_html(session_id: str) -> str:
    upload_url = f"{FUNCTION_URL}/api/upload_file?session={session_id}"
    return f"""
    <html>
    <body>
        <h1>Upload File for Session {session_id}</h1>
        <form action="{upload_url}" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Upload">
        </form>
    </body>
    </html>
    """

def get_prompt(prompt_name: str) -> str:
    # Logic to load prompt from file or return default
    return load_prompt(prompt_name)
