"""
V2V2B Interrogator - Telegram Bot for Technical Content Extraction
A serverless application that interrogates technical authors via Telegram
and processes multimodal inputs (text, audio, images) using Gemini AI.
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import base64
from pathlib import Path
import asyncio

from flask import Flask, request, jsonify, make_response
import functions_framework
from google.cloud import firestore
from google.cloud import aiplatform
from google.cloud import logging as gcp_logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
import requests

# Telegram Bot API v20+ (Async)
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
LOGS_WHITELIST = os.environ.get('LOGS_WHITELIST', '')
TARGET_FUNCTION_NAME = os.environ.get('FUNCTION_NAME', 'v2v2b-interrogator')

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

# Prompt Loading Functions and Fallbacks (Placeholder for now, will append)

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

        "multimodal_analysis_prompt.md": """# Role: Archivist
Analyze this audio or image content and extract meaningful information.
Provide structured insights including: key topics, technical concepts, action items, and areas needing clarification.
Be accurate, thorough, and well-organized in your analysis.

# Critical Instruction:
If the image contains ambiguous text, cut-off diagrams, or unclear handwriting, do NOT guess. Instead, output the specific token [CLARIFICATION_NEEDED] followed by your question.

Example:
[CLARIFICATION_NEEDED] The text in the bottom left corner is unreadable. Is it 'Function A' or 'Function B'?""",

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

Be thorough, accurate, and structured. Quality is paramount.""",

        "file_validation_prompt.md": """# Role: Archivist - File Analysis

Analyze the provided file content and generate structured notes.
Focus on extracting key technical information, decisions, and action items.
Output in Markdown format."""
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

    @staticmethod
    def save_session_data(session_id: str, data: Dict[str, Any]):
        """Save structured session data."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            session_ref.set({'session_data': data}, merge=True)
            logger.info(f"Saved session data for session {session_id}")
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
            raise

    @staticmethod
    def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve structured session data."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()
            if doc.exists:
                return doc.to_dict().get('session_data')
            return None
        except Exception as e:
            logger.error(f"Error retrieving session data: {e}")
            return None

    @staticmethod
    def delete_session_data(session_id: str):
        """Delete structured session data."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            session_ref.update({'session_data': firestore.DELETE_FIELD})
            logger.info(f"Deleted session data for session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session data: {e}")
            raise


class GoogleDriveClient:
    """Handles Google Drive operations."""

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
        """Search for Kanban file by name within the specified folder."""
        try:
            if self._kanban_file_id:
                return self._kanban_file_id

            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_client.service.files().list(
                q=query,
                fields='files(id, name, modifiedTime)',
                orderBy='modifiedTime desc'
            ).execute()

            files = results.get('files', [])
            if not files:
                return None

            self._kanban_file_id = files[0]['id']
            return self._kanban_file_id
        except Exception as e:
            logger.error(f"Error finding Kanban file: {e}", exc_info=True)
            return None

    def extract_action_items(self, note_content: str, note_title: str) -> List[Dict[str, str]]:
        """Extract action items from the '## Action Items' section of interview notes."""
        import re
        try:
            section_match = re.search(r'## Action Items\s*\n(.*?)(?=\n##|\Z)', note_content, re.DOTALL | re.MULTILINE)
            if not section_match:
                return []
            action_section = section_match.group(1)
            item_pattern = re.compile(r'-\s*\[\s*\]\s*(.+?)\s*-\s*\*\*Owner:\*\*\s*\[\[(.+?)\]\](?:\s*-\s*\*\*Due:\*\*\s*(.+?))?(?=\n|$)', re.MULTILINE)
            items = []
            for match in item_pattern.finditer(action_section):
                items.append({
                    'task': match.group(1).strip(),
                    'owner': match.group(2).strip(),
                    'due_date': match.group(3).strip() if match.group(3) else "TBD",
                    'source_note': note_title
                })
            return items
        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            return []

    def transform_to_kanban_format(self, action_items: List[Dict[str, str]], source_note_title: str) -> List[str]:
        """Transform action items from interview format to Kanban format."""
        kanban_tasks = []
        for item in action_items:
            task_line = f"- [ ] #Maestro **Task:** {item['task']} - Owner: [[{item['owner']}]] - Due: {item['due_date']}"
            source_line = f"  - Source: [[{source_note_title}]]"
            kanban_tasks.append(f"{task_line}\n{source_line}")
        return kanban_tasks

    def parse_kanban_content(self, content: str) -> Dict[str, Any]:
        """Parse Kanban markdown file structure."""
        import re
        result = {'frontmatter': '', 'sections': {}, 'settings': '', 'original_content': content}
        try:
            fm_match = re.search(r'^(---\s*\n.*?\n---\s*\n)', content, re.DOTALL | re.MULTILINE)
            if fm_match:
                result['frontmatter'] = fm_match.group(1)

            settings_match = re.search(r'(%% kanban:settings.*?%%)', content, re.DOTALL)
            if settings_match:
                result['settings'] = settings_match.group(1)

            section_pattern = re.compile(r'^## (.+?)$', re.MULTILINE)
            sections = list(section_pattern.finditer(content))

            for i, match in enumerate(sections):
                section_name = match.group(1).strip()
                start = match.end()
                if i + 1 < len(sections):
                    end = sections[i + 1].start()
                elif settings_match:
                    end = settings_match.start()
                else:
                    end = len(content)
                result['sections'][section_name] = {
                    'start_index': start,
                    'end_index': end,
                    'content': content[start:end].strip(),
                    'heading': match.group(0)
                }
            return result
        except Exception as e:
            logger.error(f"Error parsing Kanban content: {e}", exc_info=True)
            return result

    def insert_tasks_into_kanban(self, parsed_kanban: Dict[str, Any], new_tasks: List[str]) -> str:
        """Insert new tasks into the '## New' column of Kanban board."""
        import re
        try:
            if 'New' not in parsed_kanban['sections']:
                return parsed_kanban['original_content']

            new_section = parsed_kanban['sections']['New']
            updated_new_content = new_section['content']
            if updated_new_content.strip():
                updated_new_content += "\n\n"
            updated_new_content += "\n\n".join(new_tasks)

            updated_content = parsed_kanban['frontmatter'] or ""

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

            if parsed_kanban['settings']:
                updated_content += parsed_kanban['settings']

            return updated_content
        except Exception as e:
            logger.error(f"Error inserting tasks into Kanban: {e}", exc_info=True)
            return parsed_kanban['original_content']

    def update_kanban_board(self, action_items: List[Dict[str, str]], source_note_title: str) -> bool:
        """Main method to update Kanban board with new action items."""
        try:
            if not action_items:
                return True
            if not self._kanban_folder_id:
                return False

            kanban_file_id = self.find_kanban_file(self._kanban_folder_id)
            if not kanban_file_id:
                return False

            content_bytes = self.drive_client.download_file(kanban_file_id)
            if not content_bytes:
                return False
            content = content_bytes.decode('utf-8')

            parsed = self.parse_kanban_content(content)
            kanban_tasks = self.transform_to_kanban_format(action_items, source_note_title)
            updated_content = self.insert_tasks_into_kanban(parsed, kanban_tasks)

            return self.drive_client.update_file_content(kanban_file_id, updated_content)
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

    def sync_to_obsidian(self, filename: str, content: str, summary: str, tags: List[str], metadata: Dict[str, Any]) -> Optional[str]:
        """Upload markdown note to Obsidian Drive folder."""
        try:
            if not OBSIDIAN_DRIVE_FOLDER_ID:
                logger.warning("OBSIDIAN_DRIVE_FOLDER_ID not configured, skipping sync")
                return None

            base_name = filename.rsplit('.', 1)[0]
            md_filename = f"{base_name}.md"

            frontmatter = "---\n"
            frontmatter += f"title: {base_name}\n"
            frontmatter += f"created: {metadata.get('createdTime', datetime.utcnow().isoformat())}\n"
            frontmatter += f"source: Google Drive\n"
            frontmatter += f"file_id: {metadata.get('file_id', '')}\n"
            if tags:
                frontmatter += f"tags: [{', '.join(tags)}]\n"
            frontmatter += "---\n\n"

            note = frontmatter
            note += f"# {base_name}\n\n"
            note += f"## Summary\n\n{summary}\n\n"
            note += f"## Full Content\n\n{content}\n\n"

            return self.drive_client.upload_file(
                folder_id=OBSIDIAN_DRIVE_FOLDER_ID,
                filename=md_filename,
                content=note,
                mime_type='text/markdown'
            )
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
            part = Part.from_data(data=audio_data, mime_type='audio/mp4')
            prompt_part = Part.from_text("Transcribe this audio recording. Provide a clean, accurate transcription of all spoken content.")
            response = self.gemini.model.generate_content([prompt_part, part])
            return response.text
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

    def chat_response(self, user_message: str, history: List[Dict[str, str]], session_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a chat response with context."""
        try:
            contents = []

            # System Instruction
            contents.append(Content(role="user", parts=[Part.from_text(get_prompt('telegram_chat_prompt.md'))]))
            contents.append(Content(role="model", parts=[Part.from_text("Understood. I'm ready to conduct the technical interview with appropriate sarcasm and depth.")]))

            # Session Data Context
            if session_data:
                context_message = f"Here is the current session data for your reference:\n\n```json\n{json.dumps(session_data, indent=2)}\n```\n\nUse this data to inform your responses."
                contents.append(Content(role="user", parts=[Part.from_text(context_message)]))
                contents.append(Content(role="model", parts=[Part.from_text("Understood. I will use the provided session data as context.")]))

            # History
            for msg in history:
                role = "user" if msg['role'] == 'user' else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg['content'])]))

            # Current Message
            contents.append(Content(role="user", parts=[Part.from_text(user_message)]))

            response = self.model.generate_content(contents)
            return response.text
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I seem to be experiencing technical difficulties. How ironic."

    def analyze_multimodal(self, file_data: bytes, mime_type: str, filename: str) -> str:
        """Analyze audio, image, video, or PDF file."""
        try:
            if mime_type.startswith(('image/', 'audio/', 'video/')) or mime_type == 'application/pdf':
                part = Part.from_data(data=file_data, mime_type=mime_type)
            else:
                return f"Unsupported file type: {mime_type}"

            base_prompt = get_prompt('multimodal_analysis_prompt.md')
            prompt_text = f"{base_prompt}\n\nFile: {filename}"

            if "[CLARIFICATION_NEEDED]" not in prompt_text:
                prompt_text += "\n\nCRITICAL: If the content is ambiguous, unclear, or cut-off, do NOT guess. Output [CLARIFICATION_NEEDED] followed by your question."

            prompt_part = Part.from_text(prompt_text)
            response = self.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
            return f"Error analyzing file: {str(e)}"


class RepositoryConfig:
    """Data class for repository configuration."""
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
            if not self._token:
                raise ValueError(f"Token not found for {self.token_env_var}")
        return self._token

    def get_github_client(self):
        if self._github_client is None:
            self._github_client = Github(self.token)
        return self._github_client

    def get_repo(self):
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
        self.repositories = {}
        self.routing_rules = {}
        self.default_repo_label = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            for repo_data in data.get('repositories', []):
                label = repo_data['label']
                self.repositories[label] = RepositoryConfig(
                    repo_data['name'],
                    label,
                    repo_data['token_env_var'],
                    repo_data.get('description', ''),
                    repo_data.get('paths', {})
                )

            self.default_repo_label = data.get('default_repository')
            self.routing_rules = data.get('routing_rules', {})
        except Exception as e:
            logger.error(f"Failed to load repository configuration: {e}")
            raise

    def get_repo_config(self, label: str = None, name: str = None) -> RepositoryConfig:
        if label:
            return self.repositories.get(label)
        if name:
            for repo in self.repositories.values():
                if repo.name == name:
                    return repo
        return self.repositories[self.default_repo_label]

    def get_default_repo_for_operation(self, operation: str) -> RepositoryConfig:
        rule = self.routing_rules.get(operation)
        if rule and 'default_target' in rule:
            return self.get_repo_config(label=rule['default_target'])
        return self.get_repo_config()


class GitHubManager:
    """Handles GitHub operations for PR creation."""

    def __init__(self, config_path: str = None):
        self.config_manager = GitHubConfigManager.get_instance(config_path)

    def _get_repo_for_operation(self, operation: str, repo_label: Optional[str] = None, repo_name: Optional[str] = None) -> RepositoryConfig:
        if repo_label or repo_name:
            return self.config_manager.get_repo_config(label=repo_label, name=repo_name)
        return self.config_manager.get_default_repo_for_operation(operation)

    def create_pr_from_session(self, session_id: str, history: List[Dict[str, str]], repo_label: Optional[str] = None) -> str:
        repo_config = self._get_repo_for_operation('sessions', repo_label)
        repo = repo_config.get_repo()

        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        safe_id = session_id.replace('@', '-').replace('.', '-')
        branch_name = f"session/{safe_id}-{timestamp}"

        default_branch = repo.default_branch
        source_sha = repo.get_branch(default_branch).commit.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

        markdown = f"# Session: {session_id}\n\n"
        for msg in history:
            markdown += f"## {msg['role'].upper()}\n{msg['content']}\n\n"

        base_path = repo_config.paths.get('sessions', 'sessions/')
        filename = f"{base_path}{datetime.utcnow().strftime('%Y-%m-%d')}-{safe_id}.md"

        repo.create_file(path=filename, message=f"Add session {session_id}", content=markdown, branch=branch_name)
        pr = repo.create_pull(title=f"Session: {session_id}", body="Automated PR", head=branch_name, base=default_branch)
        return pr.html_url

    def create_pr_from_transcript(self, filename: str, transcript: str, analysis: str, questions: str, metadata: Dict[str, Any]) -> str:
        repo_config = self._get_repo_for_operation('transcripts')
        repo = repo_config.get_repo()

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"transcript/{filename.replace(' ', '-')}-{timestamp}"

        default_branch = repo.default_branch
        source_sha = repo.get_branch(default_branch).commit.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

        content = f"# Analysis\n{analysis}\n\n# Questions\n{questions}\n\n# Transcript\n{transcript}"
        base_path = repo_config.paths.get('transcripts', 'transcripts/')
        file_path = f"{base_path}{datetime.now().strftime('%Y-%m-%d')}-{filename}.md"

        repo.create_file(path=file_path, message=f"Analysis: {filename}", content=content, branch=branch_name)
        pr = repo.create_pull(title=f"Transcript: {filename}", body=f"Analysis of {filename}", head=branch_name, base=default_branch)
        return pr.html_url

    def create_pr_from_interview(self, title: str, content: str, session_id: str, repo_label: str = 'beyond', target_path: str = None) -> str:
        repo_config = self._get_repo_for_operation('interviews', repo_label)
        repo = repo_config.get_repo()

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        safe_title = title.replace(' ', '-')[:50]
        branch_name = f"interview/{safe_title}-{timestamp}"

        default_branch = repo.default_branch
        source_sha = repo.get_branch(default_branch).commit.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

        if target_path is None:
            target_path = repo_config.paths.get('interviews', '05_Maestro_Notes/')

        filename = f"{target_path}{datetime.now(timezone.utc).strftime('%Y-%m-%d')} - {title}.md"
        repo.create_file(path=filename, message=f"Interview: {title}", content=content, branch=branch_name)

        pr = repo.create_pull(title=f"Interview: {title}", body=f"Session: {session_id}", head=branch_name, base=default_branch)
        return pr.html_url


class TelegramClient:
    """Handles Telegram Bot API operations using synchronous requests for HTTP handlers."""
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        self.token = TELEGRAM_BOT_TOKEN

    def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode: str = 'Markdown') -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': text[:4096]}
            if parse_mode: payload['parse_mode'] = parse_mode
            if reply_markup: payload['reply_markup'] = reply_markup.to_json()

            response = requests.post(url, json=payload, timeout=10)
            if not response.json().get('ok') and parse_mode:
                 payload.pop('parse_mode')
                 response = requests.post(url, json=payload, timeout=10)

            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"TelegramClient error: {e}")
            return False


# --------------------------------------------------------------------------------
# ASYNC BOT HANDLERS & LOGIC
# --------------------------------------------------------------------------------

def fetch_gcp_logs(function_name: str) -> List[str]:
    """Fetches ERROR and CRITICAL logs for the specified Cloud Function within the last 5 minutes."""
    try:
        client = gcp_logging.Client(project=GCP_PROJECT)
        five_mins_ago = (datetime.utcnow() - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        # Filter: Specific function, Severity >= ERROR, Time >= 5 mins ago
        filter_str = (
            f'resource.type="cloud_function" AND '
            f'resource.labels.function_name="{function_name}" AND '
            f'severity >= ERROR AND '
            f'timestamp >= "{five_mins_ago}"'
        )

        entries = client.list_entries(filter_=filter_str, order_by=gcp_logging.DESCENDING, page_size=20)

        logs = []
        for entry in entries:
            timestamp = entry.timestamp.strftime('%H:%M:%S')
            severity = entry.severity or "ERROR"

            payload = entry.payload
            if isinstance(payload, dict):
                message = json.dumps(payload)
            else:
                message = str(payload)

            # Truncate individual log message to avoid one huge log eating the whole buffer
            if len(message) > 300:
                message = message[:300] + "..."

            logs.append(f"[{timestamp}] {severity}: {message}")

        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise


async def logs_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram handler for /logs command."""
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # 1. Authorization Check
        if LOGS_WHITELIST:
            try:
                whitelist = [int(uid.strip()) for uid in LOGS_WHITELIST.split(',')]
                if user_id not in whitelist:
                    await update.message.reply_text("❌ You are not authorized to use this command.")
                    return
            except ValueError:
                logger.error("Invalid LOGS_WHITELIST format")
                await update.message.reply_text("❌ Configuration error.")
                return

        await update.message.reply_text("⏳ Fetching recent error logs...")

        # 2. Fetch Logs (blocking I/O in executor)
        loop = asyncio.get_running_loop()
        logs = await loop.run_in_executor(None, fetch_gcp_logs, TARGET_FUNCTION_NAME)

        if not logs:
            await update.message.reply_text("✅ No ERROR or CRITICAL logs found in the last 5 minutes.")
            return

        # 3. Format Output
        header = f"🔎 *Error Logs ({TARGET_FUNCTION_NAME})*\n"
        log_text = "\n".join(logs)

        full_message = f"{header}\n```\n{log_text}\n```"

        # Check Telegram length limit (4096 chars)
        if len(full_message) > 4000:
            full_message = f"{header}\n```\n{log_text[:3900]}\n... (truncated)\n```"

        await update.message.reply_text(full_message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Log retrieval failed: {e}")
        await update.message.reply_text(f"❌ Failed to fetch logs: {str(e)}")


class BotHandlers:
    """Container for async Telegram handlers."""
    def __init__(self):
        self.gemini = GeminiClient()
        self.github_manager = GitHubManager()
        self.drive_client = GoogleDriveClient()
        self.kanban_manager = KanbanManager(self.drive_client)
        self.kanban_manager._kanban_folder_id = KANBAN_FOLDER_ID

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        first_name = update.effective_user.first_name
        text = (
            f"👋 Hello {first_name}! I'm the V2V2B Interrogator.\n\n"
            "I'm a sarcastic but insightful Enterprise Architect here to extract architectural wisdom from you.\n\n"
            "**Commands:**\n"
            "/start - Show this welcome message\n"
            "/upload - Get upload link for audio/images\n"
            "/logs - Fetch recent error logs\n"
            "/done - Complete session and create PR\n"
            "/help - Show help information"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "**V2V2B Interrogator Help**\n\n"
            "**How to use:**\n"
            "1. Send text messages - I'll ask probing questions\n"
            "2. Upload .txt, .md, .pdf files directly\n"
            "3. Send voice recordings for transcription\n"
            "4. Use /logs to see system errors\n"
            "5. Use /done when finished to create a GitHub PR\n"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'system', 'Upload requested', str(update.effective_chat.id))

        upload_url = f"{FUNCTION_URL}?mode=ui&session={session_id}"
        await update.message.reply_text(f"📎 Upload Link:\n{upload_url}")

    async def done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()

        try:
            is_active = await loop.run_in_executor(None, FirestoreManager.is_interviewer_active, session_id)
            if is_active:
                await self._handle_interview_complete(update, context, session_id)
            else:
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                if not history:
                    await update.message.reply_text('❌ No session history found.')
                    return
                pr_url = await loop.run_in_executor(None, self.github_manager.create_pr_from_session, session_id, history)
                await update.message.reply_text(f'✅ Session complete! PR created:\n{pr_url}')
        except Exception as e:
            logger.error(f"Error in done handler: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def _handle_interview_complete(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str):
        await update.message.reply_text('⏳ Finalizing notes...')
        loop = asyncio.get_running_loop()

        try:
            session = await loop.run_in_executor(None, FirestoreManager.get_interviewer_session, session_id)
            if not session:
                await update.message.reply_text('❌ No active session.')
                return

            clarifications = session.get('clarifications', [])
            clar_text = "\n\n".join([f"Q: {c['question']}\nA: {c['answer']}" for c in clarifications])

            prompt = f"{get_prompt('interviewer_prompt.md')}\n\nORIGINAL: {session['original_content']}\n\nCLARIFICATIONS: {clar_text}\n\nPROCEED TO FINALIZATION."

            history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
            final_notes = await loop.run_in_executor(None, self.gemini.chat_response, prompt, history)

            # Extract title
            import re
            match = re.search(r'^#\s+(.+)$', final_notes, re.MULTILINE)
            title = match.group(1).strip() if match else f"Interview {datetime.utcnow().strftime('%Y-%m-%d')}"

            # Sync to Obsidian
            new_file_name = None
            try:
                obsidian_sync = ObsidianSync(self.drive_client)
                file_id = await loop.run_in_executor(None, lambda: obsidian_sync.sync_to_obsidian(
                    f"{title}.md", final_notes, "Maestro Interview", ['Maestro'], {'createdTime': datetime.utcnow().isoformat()}
                ))
                if file_id: new_file_name = f"{title}.md"
            except Exception as e:
                logger.error(f"Obsidian sync failed: {e}")

            # Kanban Update
            try:
                def process_kanban():
                    action_items = self.kanban_manager.extract_action_items(final_notes, title)
                    if action_items:
                        return self.kanban_manager.update_kanban_board(action_items, title), len(action_items)
                    return False, 0

                success, count = await loop.run_in_executor(None, process_kanban)
                if success:
                    await update.message.reply_text(f"📋 Added {count} items to Kanban.")
            except Exception as e:
                logger.error(f"Kanban update failed: {e}")

            # Create PR
            try:
                pr_url = await loop.run_in_executor(None, self.github_manager.create_pr_from_interview, title, final_notes, session_id)
                await update.message.reply_text(f"📝 PR created:\n{pr_url}")
            except Exception as e:
                await update.message.reply_text(f"⚠️ PR creation failed: {e}")

            await loop.run_in_executor(None, FirestoreManager.complete_interviewer_session, session_id, final_notes, str(new_file_name))
            await update.message.reply_text("✅ Interview finalized.")

        except Exception as e:
            logger.error(f"Interview completion failed: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return

        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        text = update.message.text
        loop = asyncio.get_running_loop()

        try:
            is_active = await loop.run_in_executor(None, FirestoreManager.is_interviewer_active, session_id)

            if is_active:
                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'user', text, str(update.effective_chat.id))

                # Get context for next question
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                last_q = ""
                for msg in reversed(history):
                    if msg.get('role') == 'assistant':
                        last_q = msg.get('content', '')
                        break

                await loop.run_in_executor(None, FirestoreManager.add_clarification, session_id, last_q, text)

                session = await loop.run_in_executor(None, FirestoreManager.get_interviewer_session, session_id)
                clar_text = "\n".join([f"Q: {c['question']}\nA: {c['answer']}" for c in session.get('clarifications', [])])

                prompt = f"{get_prompt('interviewer_prompt.md')}\n\nTranscript: {session['original_content']}\n\nClarifications: {clar_text}\n\nUser: {text}\n\nContinue interview."
                response = await loop.run_in_executor(None, self.gemini.chat_response, prompt, history)

                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', response, str(update.effective_chat.id))
                await update.message.reply_text(response)

            else:
                # Normal Chat
                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'user', text, str(update.effective_chat.id))
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                response = await loop.run_in_executor(None, self.gemini.chat_response, text, history)

                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', response, str(update.effective_chat.id))
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Message error: {e}")
            await update.message.reply_text("❌ Error processing message.")

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()

        try:
            file_obj = None
            filename = "unknown"
            mime_type = ""

            if message.document:
                file_obj = await message.document.get_file()
                filename = message.document.file_name or "doc"
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
                await update.message.reply_text("❌ Unsupported file.")
                return

            await update.message.reply_text(f"📄 Processing {filename}...")
            byte_array = await file_obj.download_as_bytearray()
            file_data = bytes(byte_array)

            # Analyze
            analysis = ""
            if mime_type == 'application/pdf':
                analysis = await loop.run_in_executor(None, self.gemini.analyze_multimodal, file_data, 'application/pdf', filename)
            elif mime_type.startswith('audio') or mime_type.startswith('video'):
                analysis = await loop.run_in_executor(None, self.gemini.analyze_multimodal, file_data, mime_type, filename)
            elif mime_type == 'text/plain' or filename.endswith(('.txt', '.md')):
                analysis = file_data.decode('utf-8', errors='ignore')
            else:
                await update.message.reply_text("❌ Unsupported format.")
                return

            # Start Interview
            await loop.run_in_executor(None, FirestoreManager.create_interviewer_session, session_id, None, None, analysis)

            prompt = f"{get_prompt('interviewer_prompt.md')}\n\nTRANSCRIPT:\n{analysis}"
            questions = await loop.run_in_executor(None, self.gemini.chat_response, prompt, [])

            await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', questions, str(update.effective_chat.id))
            await update.message.reply_text(f"📝 Analysis Complete. Starting interview:\n\n{questions}")

        except Exception as e:
            logger.error(f"File error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")


def init_bot() -> Application:
    """Initializes the Telegram Application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    handlers = BotHandlers()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("upload", handlers.upload))
    application.add_handler(CommandHandler("done", handlers.done))
    application.add_handler(CommandHandler("logs", logs_command_handler))

    application.add_handler(MessageHandler(filters.ATTACHMENT | filters.VOICE, handlers.handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    return application


class UploadHandler:
    """Handles file upload processing via HTTP (uses TelegramClient)."""
    def __init__(self):
        self.gemini = GeminiClient()
        self.telegram_client = TelegramClient()

    def handle(self, session_id: str, file_data: bytes, filename: str, content_type: str) -> str:
        try:
            if content_type == 'application/pdf' and len(file_data) > 15 * 1024 * 1024:
                return self._error_html('PDF too large. Max 15 MB.')

            if content_type in ['application/pdf'] or content_type.startswith(('audio/', 'image/', 'video/')):
                analysis = self.gemini.analyze_multimodal(file_data, content_type, filename)
            elif content_type == 'text/plain' or filename.endswith(('.txt', '.md')):
                analysis = file_data.decode('utf-8', errors='ignore')
            else:
                return self._error_html(f'Unsupported file type: {content_type}')

            FirestoreManager.save_message(session_id, 'assistant', f"[FILE ANALYSIS: {filename}]\n\n{analysis}")

            chat_id_str = FirestoreManager.get_space_name(session_id)
            if chat_id_str:
                try:
                    chat_id = int(chat_id_str)
                    message = f"📎 File analyzed: *{filename}*\n\n{analysis}"
                    self.telegram_client.send_message(chat_id, message)
                except ValueError:
                    logger.warning(f"Invalid chat_id format: {chat_id_str}")

            return self._success_html()
        except Exception as e:
            logger.error(f"UploadHandler error: {e}")
            return self._error_html(str(e))

    def _success_html(self) -> str:
        return """
        <!DOCTYPE html><html><body style="background:#1a1a1a;color:#00ff00;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="text-align:center;border:2px solid #00ff00;padding:40px;border-radius:10px;">
        <h1>✓ Upload Successful</h1><p>Check your chat for results.</p></div></body></html>
        """

    def _error_html(self, error: str) -> str:
        return f"""
        <!DOCTYPE html><html><body style="background:#1a1a1a;color:#ff0000;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="text-align:center;border:2px solid #ff0000;padding:40px;border-radius:10px;">
        <h1>✗ Upload Failed</h1><p>{error}</p></div></body></html>
        """


class DriveMonitorHandler:
    """Handles processing of new transcript files from Google Drive."""
    def __init__(self):
        self.drive_client = GoogleDriveClient()
        self.gemini = GeminiClient()
        self.transcript_processor = TranscriptProcessor(self.gemini)
        self.github_manager = GitHubManager()
        self.obsidian_sync = ObsidianSync(self.drive_client)

    def scan_and_process_new_files(self) -> Dict[str, Any]:
        try:
            if not GOOGLE_DRIVE_FOLDER_ID:
                return {'error': 'GOOGLE_DRIVE_FOLDER_ID not configured', 'processed': 0}

            files = self.drive_client.list_files(GOOGLE_DRIVE_FOLDER_ID, ['.txt', '.md', '.m4a'])
            processed_count = 0
            results = []

            for file in files:
                file_id = file['id']
                if KnowledgeBaseManager.is_processed(file_id): continue

                result = self.process_file(file)
                if result.get('success'):
                    processed_count += 1
                    results.append(result)

            return {'success': True, 'processed': processed_count, 'results': results}
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return {'error': str(e), 'processed': 0}

    def process_file(self, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        try:
            file_id = file_metadata['id']
            filename = file_metadata['name']
            file_data = self.drive_client.download_file(file_id)
            if not file_data: return {'success': False}

            mime_type = file_metadata.get('mimeType', '')
            if mime_type == 'application/pdf':
                analysis = self.gemini.analyze_multimodal(file_data, mime_type, filename)
                transcript = analysis
            elif 'audio' in mime_type:
                transcript = self.transcript_processor.process_audio_transcript(file_data, filename)
            else:
                transcript = file_data.decode('utf-8', errors='ignore')

            analysis = self.transcript_processor.analyze_transcript(transcript)
            questions = self.transcript_processor.generate_interrogation_questions(analysis)

            KnowledgeBaseManager.index_transcript(file_id, filename, transcript, analysis, file_metadata)

            self.obsidian_sync.sync_to_obsidian(filename, transcript, analysis, ['auto-processed'], {**file_metadata, 'file_id': file_id})
            pr_url = self.github_manager.create_pr_from_transcript(filename, transcript, analysis, questions, {**file_metadata, 'file_id': file_id})
            KnowledgeBaseManager.mark_as_processed(file_id)

            return {'success': True, 'filename': filename, 'pr_url': pr_url}
        except Exception as e:
            logger.error(f"Process file error: {e}")
            return {'success': False, 'error': str(e)}


def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def jsonify_with_cors(data, status=200):
    return add_cors_headers(make_response(jsonify(data), status))

def get_upload_ui_html(session_id: str) -> str:
    upload_url = f"{FUNCTION_URL}?mode=upload&session={session_id}"
    return f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{background:#0a0a0a;color:#00ff41;font-family:'Courier New',monospace;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
    .container{{border:2px solid #00ff41;padding:40px;border-radius:15px;text-align:center;max-width:500px}}
    button{{background:#00ff41;color:#0a0a0a;border:none;padding:15px;width:100%;font-weight:bold;cursor:pointer;margin-top:20px}}
    </style></head><body><div class="container"><h1>📎 V2V2B Upload</h1><p>Session: {session_id}</p>
    <form action="{upload_url}" method="post" enctype="multipart/form-data">
    <input type="file" name="file" required style="margin:20px 0"><button type="submit">Upload</button>
    </form></div></body></html>
    """

# --------------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------------

@functions_framework.http
def entry_point(request):
    """
    Main entry point for the Cloud Function.
    Routes requests based on method and query parameters.
    """
    if request.method == 'OPTIONS':
        return add_cors_headers(make_response('', 204))

    path = request.path
    mode = request.args.get('mode', '')
    session_id = request.args.get('session', '')

    try:
        # Route A: Telegram Webhook (POST /telegram) -> Async
        if request.method == 'POST' and path == '/telegram':
            async def handle_telegram_update():
                # Re-initialize application per request to ensure valid event loop and httpx client
                app = init_bot()
                await app.initialize()

                # Process update
                update_data = request.get_json(force=True)
                if update_data:
                    await app.process_update(Update.de_json(update_data, app.bot))

                await app.shutdown()

            asyncio.run(handle_telegram_update())
            return jsonify_with_cors({'status': 'ok'})

        # Route B: Upload UI (GET /?mode=ui)
        elif request.method == 'GET' and mode == 'ui':
            return add_cors_headers(make_response(get_upload_ui_html(session_id)))

        # Route C: File Upload (POST /?mode=upload)
        elif request.method == 'POST' and mode == 'upload':
            if 'file' not in request.files:
                return jsonify_with_cors({'error': 'No file'}, 400)
            file = request.files['file']
            handler = UploadHandler()
            html = handler.handle(session_id, file.read(), file.filename, file.content_type)
            return add_cors_headers(make_response(html))

        # Route D: Drive Scan (GET /?mode=scan)
        elif mode == 'scan' or mode == 'drive_webhook':
             handler = DriveMonitorHandler()
             result = handler.scan_and_process_new_files()
             return jsonify_with_cors(result)

        # Route E: Health Check
        return jsonify_with_cors({
            'status': 'healthy',
            'service': 'V2V2B Interrogator v2.0 (Async)',
            'async_enabled': True
        })

    except Exception as e:
        logger.error(f"Entry point error: {e}", exc_info=True)
        return jsonify_with_cors({'error': str(e)}, 500)
