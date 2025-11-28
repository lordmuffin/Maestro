"""
V2V2B Interrogator - Telegram Bot for Technical Content Extraction
A serverless application that interrogates technical authors via Telegram
and processes multimodal inputs (text, audio, images) using Gemini AI.
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import base64
from pathlib import Path


from flask import Flask, request, jsonify, make_response
import functions_framework
from google.cloud import firestore
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
import io
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level initialization logging
logger.info("=" * 80)
logger.info("V2V2B Interrogator Cloud Function - Module Loading Started")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info("=" * 80)

# Environment variables
GCP_PROJECT = os.environ.get('GCP_PROJECT')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
REPO_NAME = os.environ.get('REPO_NAME')
FUNCTION_URL = os.environ.get('FUNCTION_URL')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')
OBSIDIAN_DRIVE_FOLDER_ID = os.environ.get('OBSIDIAN_DRIVE_FOLDER_ID', '')
KANBAN_FOLDER_ID = os.environ.get('KANBAN_FOLDER_ID', '')
BEYOND_REPO_NAME = os.environ.get('BEYOND_REPO_NAME', 'lordmuffin/beyond')

# Custom MCP Configuration
MAESTRO_CUSTOM_MCP_CONFIG = os.environ.get('MAESTRO_CUSTOM_MCP_CONFIG', '{}')
CUSTOM_MCP_AUTH_KEY = os.environ.get('CUSTOM_MCP_AUTH_KEY')

# Safe integer conversion with error handling
try:
    DRIVE_POLL_INTERVAL = int(os.environ.get('DRIVE_POLL_INTERVAL', '300'))
    logger.info(f"DRIVE_POLL_INTERVAL set to {DRIVE_POLL_INTERVAL} seconds")
except ValueError as e:
    logger.warning(f"Invalid DRIVE_POLL_INTERVAL value, using default 300: {e}")
    DRIVE_POLL_INTERVAL = 300

# Log environment configuration (without exposing secrets)
logger.info("Environment configuration:")
logger.info(f"  GCP_PROJECT: {'SET' if GCP_PROJECT else 'NOT SET'}")
logger.info(f"  GITHUB_TOKEN: {'SET' if GITHUB_TOKEN else 'NOT SET'}")
logger.info(f"  TELEGRAM_BOT_TOKEN: {'SET' if TELEGRAM_BOT_TOKEN else 'NOT SET'}")
logger.info(f"  REPO_NAME: {REPO_NAME if REPO_NAME else 'NOT SET'}")
logger.info(f"  FUNCTION_URL: {FUNCTION_URL if FUNCTION_URL else 'NOT SET'}")
logger.info(f"  GOOGLE_DRIVE_FOLDER_ID: {'SET' if GOOGLE_DRIVE_FOLDER_ID else 'NOT SET'}")
logger.info(f"  OBSIDIAN_DRIVE_FOLDER_ID: {'SET' if OBSIDIAN_DRIVE_FOLDER_ID else 'NOT SET'}")
logger.info(f"  MAESTRO_CUSTOM_MCP_CONFIG: {'SET' if MAESTRO_CUSTOM_MCP_CONFIG != '{}' else 'NOT SET'}")
logger.info(f"  CUSTOM_MCP_AUTH_KEY: {'SET' if CUSTOM_MCP_AUTH_KEY else 'NOT SET'}")

# Initialize MCP Registry (Simulated)
class MCPClientRegistry:
    """Manages connections to Model Context Protocol (MCP) servers."""

    def __init__(self):
        self.config = {}
        self._load_config()

    def _load_config(self):
        """Load and parse MCP configuration from environment."""
        try:
            if MAESTRO_CUSTOM_MCP_CONFIG:
                self.config = json.loads(MAESTRO_CUSTOM_MCP_CONFIG)
                logger.info(f"Loaded MCP configuration for {len(self.config)} servers")

                # Inject auth key if available and config has a custom server
                # This assumes a single custom server or applies the key to all that need it
                # For this implementation, we'll check if 'my_custom_server' exists as per Terraform
                if CUSTOM_MCP_AUTH_KEY and 'my_custom_server' in self.config:
                    self.config['my_custom_server']['auth_token'] = CUSTOM_MCP_AUTH_KEY
                    logger.info("Injected authentication key into MCP configuration")
            else:
                logger.info("No MCP configuration found")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MAESTRO_CUSTOM_MCP_CONFIG: {e}")
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve configuration for a specific MCP server."""
        return self.config.get(server_name)

# Initialize global MCP registry
_mcp_registry = MCPClientRegistry()

# Validate critical environment variables
missing_vars = []
if not GCP_PROJECT:
    missing_vars.append('GCP_PROJECT')
if not TELEGRAM_BOT_TOKEN:
    missing_vars.append('TELEGRAM_BOT_TOKEN')

# Note: Repository configuration validation happens after GitHubConfigManager class is defined
# See validate_repo_config() function below

if missing_vars:
    logger.error(f"CRITICAL: Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Function may fail when these are accessed")
else:
    logger.info("Basic environment variables are set")

# Lazy initialization globals
_db_client = None
_vertexai_initialized = False


def get_db():
    """Lazy-load Firestore client to prevent cold start crashes."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=GCP_PROJECT)
        logger.info("Initialized Firestore client")
    return _db_client


def ensure_vertexai_initialized():
    """Lazy-load Vertex AI initialization to prevent cold start crashes."""
    global _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(project=GCP_PROJECT, location="us-central1")
        _vertexai_initialized = True
        logger.info("Initialized Vertex AI")


# Prompt Loading Functions
def load_prompt(prompt_filename: str) -> str:
    """Load a prompt from the prompts directory."""
    try:
        # Try to find prompts directory relative to this file
        prompts_dir = Path(__file__).parent.parent / "prompts"

        # If not found, try current directory (for Cloud Function deployment)
        if not prompts_dir.exists():
            prompts_dir = Path("prompts")

        prompt_path = prompts_dir / prompt_filename

        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Loaded prompt from {prompt_path}")
                return content
        else:
            logger.warning(f"Prompt file not found: {prompt_path}")
            return get_fallback_prompt(prompt_filename)
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_filename}: {e}")
        return get_fallback_prompt(prompt_filename)


def get_fallback_prompt(prompt_filename: str) -> str:
    """Return fallback prompts if files cannot be loaded."""
    fallbacks = {
        "telegram_chat_prompt.md": """You are a professional technical interview assistant for the Maestro AI Executive Assistant.
Your goal is to extract valuable technical knowledge through respectful, focused conversation.
Be professional, curious, and methodical. Ask clarifying questions to uncover design decisions,
implementation details, and architectural insights.""",

        "multimodal_analysis_prompt.md": """Analyze this audio or image content and extract meaningful information.
Provide structured insights including: key topics, technical concepts, action items, and areas needing clarification.
Be accurate, thorough, and well-organized in your analysis.""",

        "transcript_analysis_prompt.md": """Analyze this transcript and extract:
1. Key architectural concepts and design patterns mentioned
2. Technical decisions and trade-offs discussed
3. Implementation details and code examples
4. Pain points, challenges, or lessons learned
5. Questions that would help dig deeper into this topic

Provide a structured summary with clear sections.""",

        "interrogation_questions_prompt.md": """Based on this transcript analysis, generate:
1. A list of 5-10 probing questions to extract more details
2. Areas that need clarification or deeper exploration
3. Follow-up topics that should be covered
4. Connections to related architectural concepts

Format as a markdown checklist suitable for a GitHub PR.""",

        "interviewer_prompt.md": """# Role: Maestro Executive Interviewer

You are the "Interviewer" module of the Maestro AI Executive Assistant. Your goal is to convert raw transcripts into pristine, high-value Obsidian notes.

## Phase 1: Analysis
Analyze the transcript for:
- Action Items (who, what, when)
- Key Decisions (what was decided and why)
- Ambiguities (vague references, missing dates, unclear owners, ambiguous names)

Flag: "he/she/they", "the project", "next Friday", "Someone should...", "Sarah" (which Sarah?)

## Phase 2: Interrogation
If you detect ANY ambiguity:
- STOP and ask clarifying questions
- Be direct and concise
- Group related questions (max 5 at a time)
- Example: "You mentioned 'meeting with Sarah' - is that Sarah Connor or Sarah Smith?"

Only proceed to Phase 3 when user confirms facts or says "Save it" / "/DONE"

## Phase 3: Finalization
Format as Obsidian markdown with:
- YAML frontmatter (date, participants, type, tags)
- Wikilinks for people/projects: [[Name]]
- ISO dates (YYYY-MM-DD)
- Action items with owner and due date
- Sections: Summary, Key Decisions, Action Items, Discussion, Next Steps, Notes
- MUST append #Maestro tag at end

Be thorough, accurate, and structured. Quality is paramount."""
    }

    logger.warning(f"Using fallback prompt for {prompt_filename}")
    return fallbacks.get(prompt_filename, "You are a helpful AI assistant.")


# Lazy prompt loading cache
_prompts_cache = {}


def get_prompt(prompt_name: str) -> str:
    """Lazy-load prompts with caching to prevent cold start I/O issues."""
    if prompt_name not in _prompts_cache:
        _prompts_cache[prompt_name] = load_prompt(prompt_name)
        logger.info(f"Loaded and cached prompt: {prompt_name}")
    return _prompts_cache[prompt_name]


class FirestoreManager:
    """Manages Firestore operations for session history."""

    @staticmethod
    def get_session_ref(session_id: str):
        """Get Firestore document reference for a session."""
        return get_db().collection('sessions').document(session_id)

    @staticmethod
    def save_message(session_id: str, role: str, content: str, space_name: str = None):
        """Save a message to session history."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()

            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }

            if doc.exists:
                data = doc.to_dict()
                history = data.get('history', [])
                history.append(message)
                session_ref.update({
                    'history': history,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            else:
                session_ref.set({
                    'session_id': session_id,
                    'space_name': space_name,
                    'history': [message],
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            logger.info(f"Saved message to session {session_id}")
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    @staticmethod
    def get_session_history(session_id: str) -> List[Dict[str, str]]:
        """Retrieve session history."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()
            if doc.exists:
                return doc.to_dict().get('history', [])
            return []
        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []

    @staticmethod
    def get_space_name(session_id: str) -> Optional[str]:
        """Get the space name for a session."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()
            if doc.exists:
                return doc.to_dict().get('space_name')
            return None
        except Exception as e:
            logger.error(f"Error retrieving space name: {e}")
            return None

    @staticmethod
    def save_pending_validation(validation_id: str, session_id: str, chat_id: int,
                               file_type: str, filename: str, content: str,
                               structured_notes: str, file_data: bytes = None) -> None:
        """Save a file upload awaiting user validation."""
        try:
            validation_ref = get_db().collection('pending_validations').document(validation_id)
            validation_data = {
                'validation_id': validation_id,
                'session_id': session_id,
                'chat_id': chat_id,
                'file_type': file_type,
                'filename': filename,
                'content': content,
                'structured_notes': structured_notes,
                'created_at': firestore.SERVER_TIMESTAMP,
                'status': 'awaiting_validation'
            }
            # Store file_data separately if provided (for binary files)
            if file_data:
                validation_data['file_data_base64'] = base64.b64encode(file_data).decode('utf-8')

            validation_ref.set(validation_data)
            logger.info(f"Saved pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error saving pending validation: {e}")
            raise

    @staticmethod
    def get_pending_validation(validation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a pending validation."""
        try:
            validation_ref = get_db().collection('pending_validations').document(validation_id)
            doc = validation_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error retrieving pending validation: {e}")
            return None

    @staticmethod
    def delete_pending_validation(validation_id: str) -> None:
        """Delete a pending validation."""
        try:
            validation_ref = get_db().collection('pending_validations').document(validation_id)
            validation_ref.delete()
            logger.info(f"Deleted pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error deleting pending validation: {e}")
            raise

    @staticmethod
    def create_interviewer_session(session_id: str, source_file_id: Optional[str],
                                   source_file_path: Optional[str], original_content: str) -> Dict[str, Any]:
        """Create a new interviewer session for transcript refinement."""
        try:
            session_ref = get_db().collection('interviewer_sessions').document(session_id)
            session_data = {
                'session_id': session_id,
                'active': True,
                'completed': False,
                'source_file_id': source_file_id,
                'source_file_path': source_file_path,
                'original_content': original_content,
                'clarifications': [],
                'refined_notes': None,
                'started_at': firestore.SERVER_TIMESTAMP,
                'completed_at': None,
                'obsidian_path': None
            }
            session_ref.set(session_data)
            logger.info(f"Created interviewer session {session_id}")
            return session_data
        except Exception as e:
            logger.error(f"Error creating interviewer session: {e}")
            raise

    @staticmethod
    def is_interviewer_active(session_id: str) -> bool:
        """Check if an interviewer session is currently active."""
        try:
            session_ref = get_db().collection('interviewer_sessions').document(session_id)
            doc = session_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get('active', False) and not data.get('completed', False)
            return False
        except Exception as e:
            logger.error(f"Error checking interviewer session: {e}")
            return False

    @staticmethod
    def get_interviewer_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve interviewer session data."""
        try:
            session_ref = get_db().collection('interviewer_sessions').document(session_id)
            doc = session_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error retrieving interviewer session: {e}")
            return None

    @staticmethod
    def add_clarification(session_id: str, question: str, answer: str) -> None:
        """Add a Q&A clarification to the interviewer session."""
        try:
            session_ref = get_db().collection('interviewer_sessions').document(session_id)
            doc = session_ref.get()
            if doc.exists:
                data = doc.to_dict()
                clarifications = data.get('clarifications', [])
                clarifications.append({
                    'question': question,
                    'answer': answer,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                session_ref.update({
                    'clarifications': clarifications,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
                logger.info(f"Added clarification to session {session_id}")
        except Exception as e:
            logger.error(f"Error adding clarification: {e}")
            raise

    @staticmethod
    def complete_interviewer_session(session_id: str, refined_notes: str, obsidian_path: str) -> None:
        """Mark interviewer session as completed."""
        try:
            session_ref = get_db().collection('interviewer_sessions').document(session_id)
            session_ref.update({
                'active': False,
                'completed': True,
                'refined_notes': refined_notes,
                'obsidian_path': obsidian_path,
                'completed_at': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Completed interviewer session {session_id}")
        except Exception as e:
            logger.error(f"Error completing interviewer session: {e}")
            raise


class GoogleDriveClient:
    """Handles Google Drive operations for transcript monitoring."""

    def __init__(self):
        self._service = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of Drive client to prevent cold start issues."""
        if self._initialized:
            return

        try:
            credentials, _ = default()
            self._service = build('drive', 'v3', credentials=credentials)
            self._initialized = True
            logger.info("Initialized Google Drive client")
        except Exception as e:
            logger.error(f"Failed to initialize Drive client: {e}")
            raise

    @property
    def service(self):
        """Lazy-loaded Drive service."""
        self._ensure_initialized()
        return self._service

    def list_files(self, folder_id: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
        """List files in a Google Drive folder."""
        try:
            if not folder_id:
                logger.warning("No folder_id provided to list_files")
                return []

            # Build query
            query = f"'{folder_id}' in parents and trashed=false"
            if file_types:
                mime_queries = []
                for ft in file_types:
                    if ft == '.txt':
                        mime_queries.append("mimeType='text/plain'")
                    elif ft == '.m4a':
                        mime_queries.append("mimeType='audio/x-m4a' or mimeType='audio/mp4'")
                if mime_queries:
                    query += f" and ({' or '.join(mime_queries)})"

            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)",
                orderBy="createdTime desc",
                pageSize=100
            ).execute()

            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return []

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file content from Google Drive."""
        try:
            # First, get file metadata to check MIME type
            metadata = self.get_file_metadata(file_id)
            if not metadata:
                logger.error(f"Could not get metadata for file {file_id}")
                return None

            mime_type = metadata.get('mimeType', '')
            logger.info(f"Downloading file {file_id} with MIME type: {mime_type}")

            # Handle Google Docs native formats - export as plain text
            if mime_type == 'application/vnd.google-apps.document':
                logger.info(f"File is Google Doc, exporting as plain text")
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Regular file download
                request = self.service.files().get_media(fileId=file_id)

            file_data = request.execute()
            logger.info(f"Downloaded file {file_id}, size: {len(file_data)} bytes")
            return file_data
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}", exc_info=True)
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file."""
        try:
            file_meta = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size"
            ).execute()
            return file_meta
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None

    def upload_file(self, folder_id: str, filename: str, content: str, mime_type: str = 'text/markdown') -> Optional[str]:
        """Upload a file to Google Drive."""
        try:
            from googleapiclient.http import MediaInMemoryUpload

            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }

            media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            logger.info(f"Uploaded file {filename} to folder {folder_id}, file_id: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            return None

    def update_file_content(self, file_id: str, new_content: str) -> bool:
        """Update existing Google Drive file with new content (e.g., add #MaestroProcessed tag)."""
        try:
            from googleapiclient.http import MediaInMemoryUpload

            # Get current file metadata to preserve MIME type
            metadata = self.get_file_metadata(file_id)
            mime_type = metadata.get('mimeType', 'text/plain') if metadata else 'text/plain'

            # Create media upload with new content
            media = MediaInMemoryUpload(new_content.encode('utf-8'), mimetype=mime_type)

            # Update file content (preserves filename and parent folders)
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()

            logger.info(f"Updated content for file_id: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating file content in Drive: {e}")
            return False


class KanbanManager:
    """Manages Obsidian Kanban board operations."""

    def __init__(self, drive_client: 'GoogleDriveClient'):
        self.drive_client = drive_client
        self._kanban_file_id = None
        self._kanban_folder_id = None

    def find_kanban_file(self, folder_id: str, filename: str = "Personal Kanban.md") -> Optional[str]:
        """
        Search for Kanban file by name within the specified folder.

        Args:
            folder_id: Google Drive folder ID to search in
            filename: Name of the Kanban file (default: "Personal Kanban.md")

        Returns:
            File ID if found, None otherwise
        """
        try:
            # Return cached file_id if available
            if self._kanban_file_id:
                return self._kanban_file_id

            # Search for file by name in folder
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_client.service.files().list(
                q=query,
                fields='files(id, name, modifiedTime)',
                orderBy='modifiedTime desc'
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.warning(f"Kanban file '{filename}' not found in folder {folder_id}")
                return None

            if len(files) > 1:
                logger.warning(f"Multiple files named '{filename}' found, using most recent")

            # Cache and return file ID
            self._kanban_file_id = files[0]['id']
            logger.info(f"Found Kanban file: {filename} (ID: {self._kanban_file_id})")
            return self._kanban_file_id

        except Exception as e:
            logger.error(f"Error finding Kanban file: {e}", exc_info=True)
            return None

    def extract_action_items(self, note_content: str, note_title: str) -> List[Dict[str, str]]:
        """
        Extract action items from the "## Action Items" section of interview notes.

        Args:
            note_content: Full markdown content of the interview note
            note_title: Title of the interview note

        Returns:
            List of action item dictionaries with task, owner, due_date, source_note
        """
        import re

        try:
            # Find the Action Items section
            section_match = re.search(
                r'## Action Items\s*\n(.*?)(?=\n##|\Z)',
                note_content,
                re.DOTALL | re.MULTILINE
            )

            if not section_match:
                logger.info("No Action Items section found in interview note")
                return []

            action_section = section_match.group(1)

            # Match individual action items
            # Pattern: - [ ] Task - **Owner:** [[Name]] - **Due:** Date
            item_pattern = re.compile(
                r'-\s*\[\s*\]\s*(.+?)\s*-\s*\*\*Owner:\*\*\s*\[\[(.+?)\]\](?:\s*-\s*\*\*Due:\*\*\s*(.+?))?(?=\n|$)',
                re.MULTILINE
            )

            items = []
            for match in item_pattern.finditer(action_section):
                task = match.group(1).strip()
                owner = match.group(2).strip()
                due_date = match.group(3).strip() if match.group(3) else "TBD"

                items.append({
                    'task': task,
                    'owner': owner,
                    'due_date': due_date,
                    'source_note': note_title
                })

            logger.info(f"Extracted {len(items)} action items from interview note")
            return items

        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            return []

    def transform_to_kanban_format(self, action_items: List[Dict[str, str]], source_note_title: str) -> List[str]:
        """
        Transform action items from interview format to Kanban format.

        Args:
            action_items: List of action item dictionaries
            source_note_title: Title of the source interview note

        Returns:
            List of formatted Kanban task strings
        """
        kanban_tasks = []

        for item in action_items:
            # Format: - [ ] #Maestro **Task:** {task} - Owner: [[{owner}]] - Due: {due_date}
            task_line = f"- [ ] #Maestro **Task:** {item['task']} - Owner: [[{item['owner']}]] - Due: {item['due_date']}"

            # Add source link as sub-item (indented with 2 spaces)
            source_line = f"  - Source: [[{source_note_title}]]"

            # Combine task and source with newline
            kanban_tasks.append(f"{task_line}\n{source_line}")

        return kanban_tasks

    def parse_kanban_content(self, content: str) -> Dict[str, Any]:
        """
        Parse Kanban markdown file structure.

        Args:
            content: Full markdown content of Kanban file

        Returns:
            Dictionary with frontmatter, sections, and settings
        """
        import re

        result = {
            'frontmatter': '',
            'sections': {},
            'settings': '',
            'original_content': content
        }

        try:
            # Extract frontmatter
            fm_match = re.search(r'^(---\s*\n.*?\n---\s*\n)', content, re.DOTALL | re.MULTILINE)
            if fm_match:
                result['frontmatter'] = fm_match.group(1)

            # Extract settings block at end
            settings_match = re.search(r'(%% kanban:settings.*?%%)', content, re.DOTALL)
            if settings_match:
                result['settings'] = settings_match.group(1)

            # Find all ## sections
            section_pattern = re.compile(r'^## (.+?)$', re.MULTILINE)
            sections = list(section_pattern.finditer(content))

            for i, match in enumerate(sections):
                section_name = match.group(1).strip()
                start = match.end()

                # Find end of section (next ## or settings block or EOF)
                if i + 1 < len(sections):
                    end = sections[i + 1].start()
                elif settings_match:
                    end = settings_match.start()
                else:
                    end = len(content)

                section_content = content[start:end].strip()

                result['sections'][section_name] = {
                    'start_index': start,
                    'end_index': end,
                    'content': section_content,
                    'heading': match.group(0)
                }

            logger.info(f"Parsed Kanban with {len(result['sections'])} sections")
            return result

        except Exception as e:
            logger.error(f"Error parsing Kanban content: {e}", exc_info=True)
            return result

    def insert_tasks_into_kanban(self, parsed_kanban: Dict[str, Any], new_tasks: List[str]) -> str:
        """
        Insert new tasks into the "## New" column of Kanban board.

        Args:
            parsed_kanban: Parsed Kanban structure from parse_kanban_content()
            new_tasks: List of formatted task strings to insert

        Returns:
            Complete updated Kanban file content
        """
        import re

        try:
            # Check if "New" section exists
            if 'New' not in parsed_kanban['sections']:
                logger.error("'New' section not found in Kanban board")
                return parsed_kanban['original_content']

            new_section = parsed_kanban['sections']['New']

            # Build the updated New section content
            updated_new_content = new_section['content']

            # Add blank line if section already has content
            if updated_new_content.strip():
                updated_new_content += "\n\n"

            # Add new tasks with blank line between each
            updated_new_content += "\n\n".join(new_tasks)

            # Rebuild the entire file
            updated_content = ""

            # Add frontmatter
            if parsed_kanban['frontmatter']:
                updated_content += parsed_kanban['frontmatter'] + "\n"

            # Add all sections in order
            sections_in_order = []
            original = parsed_kanban['original_content']

            for section_name, section_data in parsed_kanban['sections'].items():
                heading_match = re.search(rf'^## {re.escape(section_name)}$', original, re.MULTILINE)
                if heading_match:
                    sections_in_order.append((heading_match.start(), section_name, section_data))

            sections_in_order.sort(key=lambda x: x[0])

            for _, section_name, section_data in sections_in_order:
                updated_content += f"## {section_name}\n\n"

                if section_name == 'New':
                    updated_content += updated_new_content + "\n\n"
                else:
                    updated_content += section_data['content'] + "\n\n"

            # Add settings block at end
            if parsed_kanban['settings']:
                updated_content += parsed_kanban['settings']

            return updated_content

        except Exception as e:
            logger.error(f"Error inserting tasks into Kanban: {e}", exc_info=True)
            return parsed_kanban['original_content']

    def update_kanban_board(self, action_items: List[Dict[str, str]], source_note_title: str) -> bool:
        """
        Main method to update Kanban board with new action items.

        Args:
            action_items: List of action item dictionaries
            source_note_title: Title of the source interview note

        Returns:
            True if successful, False otherwise
        """
        try:
            if not action_items:
                logger.info("No action items to add to Kanban")
                return True

            # Step 1: Find Kanban file
            if not self._kanban_folder_id:
                logger.error("KANBAN_FOLDER_ID not configured")
                return False

            kanban_file_id = self.find_kanban_file(self._kanban_folder_id)
            if not kanban_file_id:
                logger.error("Kanban file not found")
                return False

            # Step 2: Download current content
            content_bytes = self.drive_client.download_file(kanban_file_id)
            if not content_bytes:
                logger.error("Failed to download Kanban file")
                return False

            content = content_bytes.decode('utf-8')

            # Step 3: Parse Kanban structure
            parsed = self.parse_kanban_content(content)

            # Step 4: Transform action items to Kanban format
            kanban_tasks = self.transform_to_kanban_format(action_items, source_note_title)

            # Step 5: Insert tasks into New column
            updated_content = self.insert_tasks_into_kanban(parsed, kanban_tasks)

            # Step 6: Update file in Google Drive
            success = self.drive_client.update_file_content(kanban_file_id, updated_content)

            if success:
                logger.info(f"✅ Successfully added {len(action_items)} tasks to Kanban board")
                return True
            else:
                logger.error("Failed to update Kanban file in Google Drive")
                return False

        except Exception as e:
            logger.error(f"Error updating Kanban board: {e}", exc_info=True)
            return False


class KnowledgeBaseManager:
    """Manages indexed transcripts for knowledge base and RAG."""

    @staticmethod
    def index_transcript(file_id: str, filename: str, content: str, summary: str, metadata: Dict[str, Any]):
        """Index a transcript in Firestore for search and retrieval."""
        try:
            kb_ref = get_db().collection('knowledge_base').document(file_id)
            kb_ref.set({
                'file_id': file_id,
                'filename': filename,
                'content': content,
                'summary': summary,
                'metadata': metadata,
                'indexed_at': firestore.SERVER_TIMESTAMP,
                'created_time': metadata.get('createdTime'),
                'file_type': metadata.get('mimeType')
            })
            logger.info(f"Indexed transcript {filename} in knowledge base")
        except Exception as e:
            logger.error(f"Error indexing transcript: {e}")
            raise

    @staticmethod
    def search_knowledge_base(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant transcripts."""
        try:
            # Simple text search - in production, use vector embeddings
            results = []
            kb_docs = get_db().collection('knowledge_base').order_by('indexed_at', direction=firestore.Query.DESCENDING).limit(20).stream()

            for doc in kb_docs:
                data = doc.to_dict()
                # Simple keyword matching (replace with semantic search in production)
                if query.lower() in data.get('content', '').lower() or query.lower() in data.get('summary', '').lower():
                    results.append(data)
                    if len(results) >= limit:
                        break

            logger.info(f"Found {len(results)} results for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    @staticmethod
    def get_all_transcripts(limit: int = 50) -> List[Dict[str, Any]]:
        """Get all indexed transcripts."""
        try:
            docs = get_db().collection('knowledge_base').order_by('indexed_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            transcripts = [doc.to_dict() for doc in docs]
            return transcripts
        except Exception as e:
            logger.error(f"Error retrieving transcripts: {e}")
            return []

    @staticmethod
    def mark_as_processed(file_id: str):
        """Mark a file as processed to avoid duplicate processing."""
        try:
            processed_ref = get_db().collection('processed_files').document(file_id)
            processed_ref.set({
                'file_id': file_id,
                'processed_at': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logger.error(f"Error marking file as processed: {e}")

    @staticmethod
    def is_processed(file_id: str) -> bool:
        """Check if a file has already been processed."""
        try:
            doc = get_db().collection('processed_files').document(file_id).get()
            return doc.exists
        except Exception as e:
            logger.error(f"Error checking if file is processed: {e}")
            return False


class ObsidianSync:
    """Syncs summaries to Obsidian vault in Google Drive."""

    def __init__(self, drive_client: GoogleDriveClient):
        self.drive_client = drive_client

    def create_markdown_note(self, title: str, content: str, summary: str, tags: List[str], metadata: Dict[str, Any]) -> str:
        """Create a markdown note formatted for Obsidian."""
        # Create frontmatter
        frontmatter = "---\n"
        frontmatter += f"title: {title}\n"
        frontmatter += f"created: {metadata.get('createdTime', datetime.utcnow().isoformat())}\n"
        frontmatter += f"source: Google Drive\n"
        frontmatter += f"file_id: {metadata.get('file_id', '')}\n"
        if tags:
            frontmatter += f"tags: [{', '.join(tags)}]\n"
        frontmatter += "---\n\n"

        # Build note content
        note = frontmatter
        note += f"# {title}\n\n"
        note += f"## Summary\n\n{summary}\n\n"
        note += f"## Full Content\n\n{content}\n\n"
        note += f"## Metadata\n\n"
        note += f"- **File Type**: {metadata.get('mimeType', 'Unknown')}\n"
        note += f"- **Created**: {metadata.get('createdTime', 'Unknown')}\n"
        note += f"- **Size**: {metadata.get('size', 'Unknown')} bytes\n"

        return note

    def sync_to_obsidian(self, filename: str, content: str, summary: str, tags: List[str], metadata: Dict[str, Any]) -> Optional[str]:
        """Upload markdown note to Obsidian Drive folder."""
        try:
            if not OBSIDIAN_DRIVE_FOLDER_ID:
                logger.warning("OBSIDIAN_DRIVE_FOLDER_ID not configured, skipping sync")
                return None

            # Create markdown filename
            base_name = filename.rsplit('.', 1)[0]  # Remove extension
            md_filename = f"{base_name}.md"

            # Create markdown content
            md_content = self.create_markdown_note(
                title=base_name,
                content=content,
                summary=summary,
                tags=tags,
                metadata=metadata
            )

            # Upload to Obsidian folder
            file_id = self.drive_client.upload_file(
                folder_id=OBSIDIAN_DRIVE_FOLDER_ID,
                filename=md_filename,
                content=md_content,
                mime_type='text/markdown'
            )

            logger.info(f"Synced {md_filename} to Obsidian vault")
            return file_id
        except Exception as e:
            logger.error(f"Error syncing to Obsidian: {e}")
            return None


class TranscriptProcessor:
    """Processes transcript files (.txt and .m4a)."""

    def __init__(self, gemini_client):
        self.gemini = gemini_client

    def process_text_transcript(self, text_content: str) -> str:
        """Process a text transcript."""
        return text_content

    def process_audio_transcript(self, audio_data: bytes, filename: str) -> str:
        """Process an audio file (.m4a) using Gemini."""
        try:
            # Use Gemini's multimodal capabilities to transcribe audio
            logger.info(f"Transcribing audio file: {filename}")

            # Create audio part for Gemini
            part = Part.from_data(data=audio_data, mime_type='audio/mp4')
            prompt_part = Part.from_text("Transcribe this audio recording. Provide a clean, accurate transcription of all spoken content.")

            # Generate transcription
            response = self.gemini.model.generate_content([prompt_part, part])
            transcription = response.text

            logger.info(f"Successfully transcribed audio file: {filename}")
            return transcription
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return f"[Transcription failed: {str(e)}]"

    def analyze_transcript(self, transcript_text: str) -> str:
        """Analyze transcript using Gemini to extract insights."""
        try:
            prompt = f"{get_prompt('transcript_analysis_prompt.md')}\n\nTranscript:\n{transcript_text}"
            response = self.gemini.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            return f"Analysis failed: {str(e)}"

    def generate_interrogation_questions(self, analysis: str) -> str:
        """Generate interrogation questions based on analysis."""
        try:
            prompt = f"{get_prompt('interrogation_questions_prompt.md')}\n\nAnalysis:\n{analysis}"
            response = self.gemini.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return f"Question generation failed: {str(e)}"


class GeminiClient:
    """Handles interactions with Vertex AI Gemini models."""

    def __init__(self):
        ensure_vertexai_initialized()
        self.model = GenerativeModel("gemini-2.5-flash")

    def chat_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
        """Generate a chat response with context."""
        try:
            # Build conversation history
            contents = []

            # Add system instruction as first user message with context
            contents.append(Content(
                role="user",
                parts=[Part.from_text(get_prompt('telegram_chat_prompt.md'))]
            ))
            contents.append(Content(
                role="model",
                parts=[Part.from_text("Understood. I'm ready to conduct the technical interview with appropriate sarcasm and depth.")]
            ))

            # Add conversation history
            for msg in history:
                role = "user" if msg['role'] == 'user' else "model"
                contents.append(Content(
                    role=role,
                    parts=[Part.from_text(msg['content'])]
                ))

            # Add current message
            contents.append(Content(
                role="user",
                parts=[Part.from_text(user_message)]
            ))

            # Generate response
            response = self.model.generate_content(contents)
            return response.text
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I seem to be experiencing technical difficulties. How ironic for an Enterprise Architect bot."

    def analyze_multimodal(self, file_data: bytes, mime_type: str, filename: str) -> str:
        """Analyze audio, image, video, or PDF file."""
        try:
            # Create the appropriate Part based on file type
            if mime_type.startswith('image/'):
                part = Part.from_data(data=file_data, mime_type=mime_type)
            elif mime_type.startswith('audio/'):
                part = Part.from_data(data=file_data, mime_type=mime_type)
            elif mime_type.startswith('video/'):
                part = Part.from_data(data=file_data, mime_type=mime_type)
            elif mime_type == 'application/pdf':
                part = Part.from_data(data=file_data, mime_type=mime_type)
            else:
                return f"Unsupported file type: {mime_type}. Supported: image, audio, video, PDF"

            # Create prompt
            prompt_part = Part.from_text(f"{get_prompt('multimodal_analysis_prompt.md')}\n\nFile: {filename}")

            # Generate analysis
            response = self.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
            return f"Error analyzing file: {str(e)}"


class RepositoryConfig:
    """Data class for repository configuration."""

    def __init__(self, name: str, label: str, token_env_var: str,
                 description: str = "", paths: Dict[str, str] = None):
        self.name = name  # "owner/repo"
        self.label = label  # "maestro", "beyond"
        self.token_env_var = token_env_var
        self.description = description
        self.paths = paths or {}
        self._token = None
        self._github_client = None
        self._repo = None

    @property
    def token(self):
        """Lazy-loaded GitHub token from environment."""
        if self._token is None:
            self._token = os.environ.get(self.token_env_var)
            if not self._token:
                raise ValueError(f"Token not found for {self.token_env_var}")
        return self._token

    def get_github_client(self):
        """Lazy initialize GitHub client."""
        if self._github_client is None:
            self._github_client = Github(self.token)
        return self._github_client

    def get_repo(self):
        """Lazy initialize repository object."""
        if self._repo is None:
            self._repo = self.get_github_client().get_repo(self.name)
        return self._repo


class GitHubConfigManager:
    """Manages repository configurations (Singleton)."""
    _instance = None

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'repos.json')

        self.config_path = config_path
        self.config_data = None
        self.repositories = {}  # label -> RepositoryConfig
        self.routing_rules = {}
        self.default_repo_label = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: str = None):
        """Singleton pattern for config manager."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self):
        """Load and validate configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.json'):
                    self.config_data = json.load(f)
                elif self.config_path.endswith(('.yaml', '.yml')):
                    import yaml
                    self.config_data = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported config format: {self.config_path}")

            self._validate_and_parse_config()
            logger.info(f"Loaded configuration from {self.config_path}")
            logger.info(f"Configured repositories: {list(self.repositories.keys())}")
        except Exception as e:
            logger.error(f"Failed to load repository configuration: {e}")
            raise

    def _validate_and_parse_config(self):
        """Validate configuration and create repository objects."""
        # Validate version
        version = self.config_data.get('version')
        if not version or not isinstance(version, str):
            raise ValueError("Configuration must have 'version' field")

        # Parse repositories
        repos = self.config_data.get('repositories', [])
        if not repos:
            raise ValueError("Configuration must have at least one repository")

        for repo_data in repos:
            label = repo_data.get('label')
            if not label:
                raise ValueError("Each repository must have a 'label'")

            repo_config = RepositoryConfig(
                name=repo_data['name'],
                label=label,
                token_env_var=repo_data['token_env_var'],
                description=repo_data.get('description', ''),
                paths=repo_data.get('paths', {})
            )
            self.repositories[label] = repo_config

        # Parse default repository
        self.default_repo_label = self.config_data.get('default_repository')
        if self.default_repo_label not in self.repositories:
            raise ValueError(f"Default repository '{self.default_repo_label}' not found in repositories")

        # Parse routing rules
        self.routing_rules = self.config_data.get('routing_rules', {})
        for rule_name, rule_config in self.routing_rules.items():
            target = rule_config.get('default_target')
            if target and target not in self.repositories:
                raise ValueError(f"Routing rule '{rule_name}' targets unknown repository '{target}'")

    def get_repo_config(self, label: str = None, name: str = None) -> RepositoryConfig:
        """Get repository config by label or name."""
        if label:
            repo = self.repositories.get(label)
            if not repo:
                raise ValueError(f"Repository with label '{label}' not found")
            return repo

        if name:
            for repo in self.repositories.values():
                if repo.name == name:
                    return repo
            raise ValueError(f"Repository with name '{name}' not found")

        # Return default
        return self.repositories[self.default_repo_label]

    def get_default_repo_for_operation(self, operation: str) -> RepositoryConfig:
        """Get the default repository for a given operation type."""
        rule = self.routing_rules.get(operation)
        if rule and 'default_target' in rule:
            return self.get_repo_config(label=rule['default_target'])
        return self.get_repo_config()  # Fall back to default

    def list_repositories(self) -> List[Dict[str, str]]:
        """List all configured repositories with descriptions."""
        return [
            {
                'label': label,
                'name': config.name,
                'description': config.description
            }
            for label, config in self.repositories.items()
        ]


class GitHubManager:
    """Handles GitHub operations for PR creation across multiple repositories."""

    def __init__(self, config_path: str = None):
        self.config_manager = GitHubConfigManager.get_instance(config_path)
        self._initialized = True
        logger.info("GitHubManager initialized with multi-repo support")

    @staticmethod
    def _sanitize_git_ref_name(name: str, max_length: int = 50, allow_slashes: bool = False) -> str:
        """
        Sanitize a string for use in Git branch/ref names.

        Git ref naming rules enforced:
        - Cannot contain: .. ~ ^ : ? * [ \ @{ control chars
        - Cannot end with .lock . or /
        - Cannot start with -
        - Cannot be @ alone

        Args:
            name: String to sanitize
            max_length: Maximum length of result (default 50)
            allow_slashes: If False, replace / with - (default False)

        Returns:
            Sanitized string safe for Git refs

        Examples:
            >>> GitHubManager._sanitize_git_ref_name("Feature: Add Login")
            'Feature-Add-Login'
            >>> GitHubManager._sanitize_git_ref_name("Bug #123: Fix crash")
            'Bug-123-Fix-crash'
        """
        import re
        import unicodedata

        if not name or name == '@':
            return 'unnamed'

        original_name = name

        # Normalize Unicode to ASCII (handles emoji and accents)
        normalized = unicodedata.normalize('NFKD', name)
        ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')

        # Replace Git-invalid characters with hyphens
        result = re.sub(r'[~^:?*\[\\\x00-\x1f\x7f]', '-', ascii_str)
        result = result.replace('..', '-').replace('@{', '-').replace('@', '-').replace(' ', '-')

        if not allow_slashes:
            result = result.replace('/', '-')

        # Collapse consecutive hyphens
        result = re.sub(r'-+', '-', result)

        # Remove leading/trailing invalid chars
        result = result.strip('-./!')

        # Remove .lock suffix
        if result.endswith('.lock'):
            result = result[:-5]

        # Truncate to max_length
        if len(result) > max_length:
            result = result[:max_length].rstrip('-./!')

        # Log if sanitization changed the name
        if result != original_name:
            logger.debug(f"Sanitized Git ref name: '{original_name}' -> '{result}'")

        return result if result else 'unnamed'

    @staticmethod
    def _sanitize_filename(name: str, max_length: int = 200) -> str:
        """
        Sanitize a string for use in filesystem paths.

        Handles Windows and Unix restrictions:
        - Cannot contain: < > : " / \ | ? * control chars
        - Cannot end with . or space (Windows)

        Args:
            name: String to sanitize
            max_length: Maximum length of result (default 200)

        Returns:
            Sanitized string safe for filesystem paths

        Examples:
            >>> GitHubManager._sanitize_filename("Meeting: Q4 2024")
            'Meeting-Q4-2024'
            >>> GitHubManager._sanitize_filename("file/name.txt")
            'file-name-txt'
        """
        import re
        import unicodedata

        if not name:
            return 'unnamed'

        original_name = name

        # Normalize Unicode to ASCII
        normalized = unicodedata.normalize('NFKD', name)
        ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')

        # Replace filesystem-invalid characters
        result = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '-', ascii_str)

        # Collapse consecutive hyphens/spaces
        result = re.sub(r'[-\s]+', '-', result)

        # Remove leading/trailing invalid chars
        result = result.strip('-. ')

        # Truncate to max_length
        if len(result) > max_length:
            result = result[:max_length].rstrip('-. ')

        # Log if sanitization changed the name
        if result != original_name:
            logger.debug(f"Sanitized filename: '{original_name}' -> '{result}'")

        return result if result else 'unnamed'

    def _get_repo_for_operation(self, operation: str,
                                 repo_label: Optional[str] = None,
                                 repo_name: Optional[str] = None) -> RepositoryConfig:
        """
        Determine which repository to use for an operation.

        Priority:
        1. Explicitly provided repo_label
        2. Explicitly provided repo_name
        3. Default from routing rules for operation
        4. Global default repository
        """
        if repo_label or repo_name:
            return self.config_manager.get_repo_config(label=repo_label, name=repo_name)

        return self.config_manager.get_default_repo_for_operation(operation)

    def create_pr_from_session(self,
                               session_id: str,
                               history: List[Dict[str, str]],
                               repo_label: Optional[str] = None,
                               repo_name: Optional[str] = None) -> str:
        """
        Create a branch, commit session content, and open PR.

        Args:
            session_id: Session identifier
            history: Chat history
            repo_label: Target repository label (e.g., 'maestro')
            repo_name: Target repository name (e.g., 'owner/repo')

        Returns:
            PR URL
        """
        try:
            # Determine target repository
            repo_config = self._get_repo_for_operation('sessions', repo_label, repo_name)
            repo = repo_config.get_repo()

            logger.info(f"Creating session PR in repository: {repo_config.name}")

            # Generate branch name
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            safe_session_id = self._sanitize_git_ref_name(session_id, max_length=30)
            branch_name = f"session/{safe_session_id}-{timestamp}"

            # Get default branch
            default_branch = repo.default_branch
            source = repo.get_branch(default_branch)

            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Created branch: {branch_name}")

            # Format history as markdown
            markdown_content = self._format_history_as_markdown(session_id, history)

            # Get path from config or use default
            base_path = repo_config.paths.get('sessions', 'sessions/')

            # Create filename
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            filename = f"{base_path}{date_str}-{session_id.split('@')[0]}.md"

            # Commit file
            repo.create_file(
                path=filename,
                message=f"Add session content: {session_id}",
                content=markdown_content,
                branch=branch_name
            )
            logger.info(f"Committed file: {filename}")

            # Create PR
            pr = repo.create_pull(
                title=f"Session Content: {session_id}",
                body=f"Automated PR containing content from interrogation session `{session_id}`.\n\nGenerated by V2V2B Interrogator.",
                head=branch_name,
                base=default_branch
            )
            logger.info(f"Created PR in {repo_config.name}: {pr.html_url}")

            return pr.html_url
        except Exception as e:
            logger.error(f"Error creating session PR: {e}", exc_info=True)
            raise

    def create_pr_from_transcript(self,
                                  filename: str,
                                  transcript: str,
                                  analysis: str,
                                  questions: str,
                                  metadata: Dict[str, Any],
                                  repo_label: Optional[str] = None,
                                  repo_name: Optional[str] = None) -> str:
        """
        Create a PR with transcript analysis and interrogation questions.

        Args:
            filename: Original transcript filename
            transcript: Transcript text
            analysis: AI analysis of transcript
            questions: Generated questions
            metadata: File metadata
            repo_label: Target repository label
            repo_name: Target repository name

        Returns:
            PR URL
        """
        try:
            # Determine target repository
            repo_config = self._get_repo_for_operation('transcripts', repo_label, repo_name)
            repo = repo_config.get_repo()

            logger.info(f"Creating transcript PR in repository: {repo_config.name}")

            # Generate branch name from filename and timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            safe_filename = self._sanitize_git_ref_name(filename, max_length=30)
            branch_name = f"transcript/{safe_filename}-{timestamp}"

            # Get default branch
            default_branch = repo.default_branch
            source = repo.get_branch(default_branch)

            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Created branch: {branch_name}")

            # Format as markdown
            markdown_content = self._format_transcript_as_markdown(filename, transcript, analysis, questions, metadata)

            # Get path from config or use default
            base_path = repo_config.paths.get('transcripts', 'transcripts/')

            # Create filename for transcripts directory
            date_str = datetime.now().strftime('%Y-%m-%d')
            base_name = filename.rsplit('.', 1)[0]
            safe_base_name = self._sanitize_filename(base_name, max_length=100)
            file_path = f"{base_path}{date_str}-{safe_base_name}.md"

            # Commit file
            repo.create_file(
                path=file_path,
                message=f"Add transcript analysis: {filename}",
                content=markdown_content,
                branch=branch_name
            )
            logger.info(f"Committed file: {file_path}")

            # Create PR with interrogation questions
            pr_body = f"""## 📝 New Transcript Processed

**File**: `{filename}`
**Source**: Google Drive
**Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC

### 🔍 Analysis Summary

{analysis[:500]}...

### ❓ Interrogation Questions

{questions}

---

**Instructions**: Please review the full transcript in the attached file and answer the questions above. Your responses will be added to the knowledge base.

🤖 Generated by V2V2B Interrogator
"""

            pr = repo.create_pull(
                title=f"📋 Transcript Analysis: {filename}",
                body=pr_body,
                head=branch_name,
                base=default_branch
            )
            logger.info(f"Created PR in {repo_config.name}: {pr.html_url}")

            return pr.html_url
        except Exception as e:
            logger.error(f"Error creating transcript PR: {e}", exc_info=True)
            raise

    def _format_transcript_as_markdown(self, filename: str, transcript: str, analysis: str, questions: str, metadata: Dict[str, Any]) -> str:
        """Format transcript analysis as markdown."""
        lines = [
            f"# Transcript Analysis: {filename}",
            f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"**File ID**: {metadata.get('file_id', 'N/A')}",
            f"**Source**: Google Drive",
            "\n---\n",
            "\n## 📊 Analysis\n",
            analysis,
            "\n\n---\n",
            "\n## ❓ Interrogation Questions\n",
            questions,
            "\n\n---\n",
            "\n## 📄 Full Transcript\n",
            "```",
            transcript,
            "```",
            "\n\n---\n",
            "\n## 📋 Metadata\n",
            f"- **File Type**: {metadata.get('mimeType', 'Unknown')}",
            f"- **Created**: {metadata.get('createdTime', 'Unknown')}",
            f"- **Size**: {metadata.get('size', 'Unknown')} bytes",
            f"- **Drive File ID**: {metadata.get('file_id', 'N/A')}"
        ]

        return "\n".join(lines)

    def _format_history_as_markdown(self, session_id: str, history: List[Dict[str, str]]) -> str:
        """Format session history as markdown."""
        lines = [
            f"# Session: {session_id}",
            f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "\n---\n"
        ]

        for msg in history:
            role = msg['role'].upper()
            content = msg['content']
            timestamp = msg.get('timestamp', 'N/A')
            lines.append(f"## {role} ({timestamp})\n")
            lines.append(f"{content}\n")
            lines.append("\n---\n")

        return "\n".join(lines)

    def create_pr_from_interview(self,
                                 title: str,
                                 content: str,
                                 session_id: str,
                                 repo_label: Optional[str] = None,
                                 repo_name: Optional[str] = None,
                                 target_path: Optional[str] = None) -> str:
        """
        Create a PR in specified repo with interview notes.

        Args:
            title: Title for the interview notes
            content: Full markdown content with frontmatter
            session_id: Unique session identifier
            repo_label: Target repository label (e.g., 'beyond')
            repo_name: Target repository name (e.g., 'owner/repo')
            target_path: Directory path within repo (optional, uses config default)

        Returns:
            PR URL

        Raises:
            Exception if PR creation fails
        """
        try:
            # Determine target repository
            repo_config = self._get_repo_for_operation('interviews', repo_label, repo_name)
            repo = repo_config.get_repo()

            logger.info(f"Creating interview PR in repository: {repo_config.name}")

            # Generate branch name
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
            safe_title = self._sanitize_git_ref_name(title, max_length=50)
            branch_name = f"interview/{safe_title}-{timestamp}"

            # Get default branch and create new branch
            default_branch = repo.default_branch
            source = repo.get_branch(default_branch)
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )

            # Determine target path
            if target_path is None:
                target_path = repo_config.paths.get('interviews', '05_Maestro_Notes/')

            # Create filename with date prefix
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            safe_title_for_file = self._sanitize_filename(title, max_length=150)
            filename = f"{target_path}{date_str} - {safe_title_for_file}.md"

            # Commit file
            commit_message = f"Add interview notes: {title}\n\nSession: {session_id}\nGenerated by Maestro interviewer"
            repo.create_file(
                path=filename,
                message=commit_message,
                content=content,
                branch=branch_name
            )

            # Create PR
            pr_body = f"""## Interview Notes

**Session ID:** {session_id}
**Generated:** {date_str}

New structured interview notes generated by Maestro's AI interviewer.

---
🤖 Generated with [Maestro](https://github.com/lordmuffin/Maestro)
"""

            pr = repo.create_pull(
                title=f"Interview: {title}",
                body=pr_body,
                head=branch_name,
                base=default_branch
            )

            logger.info(f"Created PR in {repo_config.name}: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            logger.error(f"Failed to create interview PR: {e}", exc_info=True)
            raise
