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
<<<<<<< HEAD

=======
import io
import asyncio
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7

from flask import Flask, request, jsonify, make_response
import functions_framework
from google.cloud import firestore
from google.cloud import aiplatform
<<<<<<< HEAD
from google.cloud import logging as gcp_logging
=======
from google.cloud import logging as cloud_logging
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
<<<<<<< HEAD
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
import io
import requests

=======
import requests

# Telegram Bot API v20+
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

>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
LOGS_WHITELIST = os.environ.get('LOGS_WHITELIST', '')
=======
TARGET_FUNCTION_NAME = "YOUR_FUNCTION_NAME"  # Placeholder
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7

# Safe integer conversion with error handling
try:
    DRIVE_POLL_INTERVAL = int(os.environ.get('DRIVE_POLL_INTERVAL', '300'))
    logger.info(f"DRIVE_POLL_INTERVAL set to {DRIVE_POLL_INTERVAL} seconds")
except ValueError as e:
    logger.warning(f"Invalid DRIVE_POLL_INTERVAL value, using default 300: {e}")
    DRIVE_POLL_INTERVAL = 300

<<<<<<< HEAD
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

=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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

<<<<<<< HEAD
=======
# Prompt Loading Functions and Fallbacks (Placeholder for now, will append)
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7

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

<<<<<<< HEAD
        "multimodal_analysis_prompt.md": """# Role: Archivist
Analyze this audio or image content and extract meaningful information.
Provide structured insights including: key topics, technical concepts, action items, and areas needing clarification.
Be accurate, thorough, and well-organized in your analysis.

# Critical Instruction:
If the image contains ambiguous text, cut-off diagrams, or unclear handwriting, do NOT guess. Instead, output the specific token [CLARIFICATION_NEEDED] followed by your question.

Example:
[CLARIFICATION_NEEDED] The text in the bottom left corner is unreadable. Is it 'Function A' or 'Function B'?""",
=======
        "multimodal_analysis_prompt.md": """Analyze this audio or image content and extract meaningful information.
Provide structured insights including: key topics, technical concepts, action items, and areas needing clarification.
Be accurate, thorough, and well-organized in your analysis.""",
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7

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
<<<<<<< HEAD

    @staticmethod
    def get_session_ref(session_id: str):
        """Get Firestore document reference for a session."""
=======
    @staticmethod
    def get_session_ref(session_id: str):
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        return get_db().collection('sessions').document(session_id)

    @staticmethod
    def save_message(session_id: str, role: str, content: str, space_name: str = None):
<<<<<<< HEAD
        """Save a message to session history."""
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()

=======
        try:
            session_ref = FirestoreManager.get_session_ref(session_id)
            doc = session_ref.get()
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }
<<<<<<< HEAD

=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Retrieve session history."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Get the space name for a session."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Save a file upload awaiting user validation."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
            # Store file_data separately if provided (for binary files)
            if file_data:
                validation_data['file_data_base64'] = base64.b64encode(file_data).decode('utf-8')

=======
            if file_data:
                validation_data['file_data_base64'] = base64.b64encode(file_data).decode('utf-8')
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            validation_ref.set(validation_data)
            logger.info(f"Saved pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error saving pending validation: {e}")
            raise

    @staticmethod
    def get_pending_validation(validation_id: str) -> Optional[Dict[str, Any]]:
<<<<<<< HEAD
        """Retrieve a pending validation."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Delete a pending validation."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Create a new interviewer session for transcript refinement."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Check if an interviewer session is currently active."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Retrieve interviewer session data."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Add a Q&A clarification to the interviewer session."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Mark interviewer session as completed."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
    """Handles Google Drive operations for transcript monitoring."""
=======
    """Handles Google Drive operations."""
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7

    def __init__(self):
        self._service = None
        self._initialized = False

    def _ensure_initialized(self):
<<<<<<< HEAD
        """Lazy initialization of Drive client to prevent cold start issues."""
        if self._initialized:
            return

=======
        if self._initialized:
            return
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD
        """Lazy-loaded Drive service."""
=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        self._ensure_initialized()
        return self._service

    def list_files(self, folder_id: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
<<<<<<< HEAD
        """List files in a Google Drive folder."""
        try:
            if not folder_id:
                logger.warning("No folder_id provided to list_files")
                return []

            # Build query
=======
        try:
            if not folder_id:
                return []
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
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
<<<<<<< HEAD

            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
=======
            return results.get('files', [])
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return []

    def download_file(self, file_id: str) -> Optional[bytes]:
<<<<<<< HEAD
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
=======
        try:
            metadata = self.get_file_metadata(file_id)
            if not metadata:
                return None
            mime_type = metadata.get('mimeType', '')
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            else:
                request = self.service.files().get_media(fileId=file_id)
            return request.execute()
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}", exc_info=True)
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
<<<<<<< HEAD
        """Get metadata for a file."""
        try:
            file_meta = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size"
            ).execute()
            return file_meta
=======
        try:
            return self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size"
            ).execute()
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None

    def upload_file(self, folder_id: str, filename: str, content: str, mime_type: str = 'text/markdown') -> Optional[str]:
<<<<<<< HEAD
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
=======
        try:
            from googleapiclient.http import MediaInMemoryUpload
            file_metadata = {'name': filename, 'parents': [folder_id]}
            media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            return file.get('id')
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            return None

    def update_file_content(self, file_id: str, new_content: str) -> bool:
<<<<<<< HEAD
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
=======
        try:
            from googleapiclient.http import MediaInMemoryUpload
            metadata = self.get_file_metadata(file_id)
            mime_type = metadata.get('mimeType', 'text/plain') if metadata else 'text/plain'
            media = MediaInMemoryUpload(new_content.encode('utf-8'), mimetype=mime_type)
            self.service.files().update(fileId=file_id, media_body=media).execute()
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            return True
        except Exception as e:
            logger.error(f"Error updating file content in Drive: {e}")
            return False


class KanbanManager:
    """Manages Obsidian Kanban board operations."""
<<<<<<< HEAD

=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
    def __init__(self, drive_client: 'GoogleDriveClient'):
        self.drive_client = drive_client
        self._kanban_file_id = None
        self._kanban_folder_id = None

    def find_kanban_file(self, folder_id: str, filename: str = "Personal Kanban.md") -> Optional[str]:
<<<<<<< HEAD
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

=======
        try:
            if self._kanban_file_id: return self._kanban_file_id
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_client.service.files().list(q=query, fields='files(id, name, modifiedTime)', orderBy='modifiedTime desc').execute()
            files = results.get('files', [])
            if not files: return None
            self._kanban_file_id = files[0]['id']
            return self._kanban_file_id
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error finding Kanban file: {e}", exc_info=True)
            return None

    def extract_action_items(self, note_content: str, note_title: str) -> List[Dict[str, str]]:
<<<<<<< HEAD
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

=======
        import re
        try:
            section_match = re.search(r'## Action Items\s*\n(.*?)(?=\n##|\Z)', note_content, re.DOTALL | re.MULTILINE)
            if not section_match: return []
            action_section = section_match.group(1)
            item_pattern = re.compile(r'-\s*\[\s*\]\s*(.+?)\s*-\s*\*\*Owner:\*\*\s*\[\[(.+?)\]\](?:\s*-\s*\*\*Due:\*\*\s*(.+?))?(?=\n|$)', re.MULTILINE)
            items = []
            for match in item_pattern.finditer(action_section):
                items.append({'task': match.group(1).strip(), 'owner': match.group(2).strip(), 'due_date': match.group(3).strip() if match.group(3) else "TBD", 'source_note': note_title})
            return items
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            return []

    def transform_to_kanban_format(self, action_items: List[Dict[str, str]], source_note_title: str) -> List[str]:
<<<<<<< HEAD
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
=======
        kanban_tasks = []
        for item in action_items:
            task_line = f"- [ ] #Maestro **Task:** {item['task']} - Owner: [[{item['owner']}]] - Due: {item['due_date']}"
            source_line = f"  - Source: [[{source_note_title}]]"
            kanban_tasks.append(f"{task_line}\n{source_line}")
        return kanban_tasks

    def parse_kanban_content(self, content: str) -> Dict[str, Any]:
        import re
        result = {'frontmatter': '', 'sections': {}, 'settings': '', 'original_content': content}
        try:
            fm_match = re.search(r'^(---\s*\n.*?\n---\s*\n)', content, re.DOTALL | re.MULTILINE)
            if fm_match: result['frontmatter'] = fm_match.group(1)
            settings_match = re.search(r'(%% kanban:settings.*?%%)', content, re.DOTALL)
            if settings_match: result['settings'] = settings_match.group(1)
            section_pattern = re.compile(r'^## (.+?)$', re.MULTILINE)
            sections = list(section_pattern.finditer(content))
            for i, match in enumerate(sections):
                section_name = match.group(1).strip()
                start = match.end()
                if i + 1 < len(sections): end = sections[i + 1].start()
                elif settings_match: end = settings_match.start()
                else: end = len(content)
                result['sections'][section_name] = {'start_index': start, 'end_index': end, 'content': content[start:end].strip(), 'heading': match.group(0)}
            return result
        except Exception as e:
            logger.error(f"Error parsing Kanban: {e}", exc_info=True)
            return result

    def insert_tasks_into_kanban(self, parsed_kanban: Dict[str, Any], new_tasks: List[str]) -> str:
        import re
        try:
            if 'New' not in parsed_kanban['sections']: return parsed_kanban['original_content']
            new_section = parsed_kanban['sections']['New']
            updated_new_content = new_section['content']
            if updated_new_content.strip(): updated_new_content += "\n\n"
            updated_new_content += "\n\n".join(new_tasks)
            updated_content = parsed_kanban['frontmatter'] + "\n" if parsed_kanban['frontmatter'] else ""
            sections_in_order = []
            original = parsed_kanban['original_content']
            for section_name, section_data in parsed_kanban['sections'].items():
                heading_match = re.search(rf'^## {re.escape(section_name)}$', original, re.MULTILINE)
                if heading_match: sections_in_order.append((heading_match.start(), section_name, section_data))
            sections_in_order.sort(key=lambda x: x[0])
            for _, section_name, section_data in sections_in_order:
                updated_content += f"## {section_name}\n\n"
                if section_name == 'New': updated_content += updated_new_content + "\n\n"
                else: updated_content += section_data['content'] + "\n\n"
            if parsed_kanban['settings']: updated_content += parsed_kanban['settings']
            return updated_content
        except Exception as e:
            logger.error(f"Error inserting tasks: {e}", exc_info=True)
            return parsed_kanban['original_content']

    def update_kanban_board(self, action_items: List[Dict[str, str]], source_note_title: str) -> bool:
        try:
            if not action_items: return True
            if not self._kanban_folder_id: return False
            kanban_file_id = self.find_kanban_file(self._kanban_folder_id)
            if not kanban_file_id: return False
            content_bytes = self.drive_client.download_file(kanban_file_id)
            if not content_bytes: return False
            content = content_bytes.decode('utf-8')
            parsed = self.parse_kanban_content(content)
            kanban_tasks = self.transform_to_kanban_format(action_items, source_note_title)
            updated_content = self.insert_tasks_into_kanban(parsed, kanban_tasks)
            return self.drive_client.update_file_content(kanban_file_id, updated_content)
        except Exception as e:
            logger.error(f"Error updating Kanban: {e}", exc_info=True)
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            return False


class KnowledgeBaseManager:
<<<<<<< HEAD
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
=======
    """Manages indexed transcripts."""
    @staticmethod
    def index_transcript(file_id: str, filename: str, content: str, summary: str, metadata: Dict[str, Any]):
        try:
            kb_ref = get_db().collection('knowledge_base').document(file_id)
            kb_ref.set({
                'file_id': file_id, 'filename': filename, 'content': content, 'summary': summary,
                'metadata': metadata, 'indexed_at': firestore.SERVER_TIMESTAMP,
                'created_time': metadata.get('createdTime'), 'file_type': metadata.get('mimeType')
            })
            logger.info(f"Indexed transcript {filename}")
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error indexing transcript: {e}")
            raise

    @staticmethod
<<<<<<< HEAD
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
=======
    def is_processed(file_id: str) -> bool:
        try:
            return get_db().collection('processed_files').document(file_id).get().exists
        except Exception as e:
            logger.error(f"Error checking processed: {e}")
            return False

    @staticmethod
    def mark_as_processed(file_id: str):
        try:
            get_db().collection('processed_files').document(file_id).set({'file_id': file_id, 'processed_at': firestore.SERVER_TIMESTAMP})
        except Exception as e:
            logger.error(f"Error marking processed: {e}")


class ObsidianSync:
    """Syncs summaries to Obsidian vault."""
    def __init__(self, drive_client: GoogleDriveClient):
        self.drive_client = drive_client

    def sync_to_obsidian(self, filename: str, content: str, summary: str, tags: List[str], metadata: Dict[str, Any]) -> Optional[str]:
        try:
            if not OBSIDIAN_DRIVE_FOLDER_ID: return None
            base_name = filename.rsplit('.', 1)[0]
            md_filename = f"{base_name}.md"
            frontmatter = f"---\ntitle: {base_name}\ncreated: {metadata.get('createdTime')}\nsource: Google Drive\nfile_id: {metadata.get('file_id')}\ntags: [{', '.join(tags)}]\n---\n\n"
            note = f"{frontmatter}# {base_name}\n\n## Summary\n\n{summary}\n\n## Full Content\n\n{content}\n"
            return self.drive_client.upload_file(OBSIDIAN_DRIVE_FOLDER_ID, md_filename, note, 'text/markdown')
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error syncing to Obsidian: {e}")
            return None


class TranscriptProcessor:
<<<<<<< HEAD
    """Processes transcript files (.txt and .m4a)."""

=======
    """Processes transcript files."""
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
    def __init__(self, gemini_client):
        self.gemini = gemini_client

    def process_text_transcript(self, text_content: str) -> str:
<<<<<<< HEAD
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
=======
        return text_content

    def process_audio_transcript(self, audio_data: bytes, filename: str) -> str:
        try:
            part = Part.from_data(data=audio_data, mime_type='audio/mp4')
            prompt_part = Part.from_text("Transcribe this audio recording.")
            response = self.gemini.model.generate_content([prompt_part, part])
            return response.text
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return f"[Transcription failed: {str(e)}]"

    def analyze_transcript(self, transcript_text: str) -> str:
<<<<<<< HEAD
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
=======
        try:
            prompt = f"{get_prompt('transcript_analysis_prompt.md')}\n\nTranscript:\n{transcript_text}"
            return self.gemini.model.generate_content(prompt).text
        except Exception as e:
            logger.error(f"Error analyzing: {e}")
            return f"Analysis failed: {str(e)}"

    def generate_interrogation_questions(self, analysis: str) -> str:
        try:
            prompt = f"{get_prompt('interrogation_questions_prompt.md')}\n\nAnalysis:\n{analysis}"
            return self.gemini.model.generate_content(prompt).text
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return f"Question generation failed: {str(e)}"


class GeminiClient:
    """Handles interactions with Vertex AI Gemini models."""
<<<<<<< HEAD

=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
    def __init__(self):
        ensure_vertexai_initialized()
        self.model = GenerativeModel("gemini-2.5-flash")

    def chat_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
<<<<<<< HEAD
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
            # Check for Archivist specific instruction in the prompt
            base_prompt = get_prompt('multimodal_analysis_prompt.md')
            prompt_text = f"{base_prompt}\n\nFile: {filename}"

            # If not already present (e.g. from file override), ensure instruction is added
            if "[CLARIFICATION_NEEDED]" not in prompt_text:
                prompt_text += "\n\nCRITICAL: If the content is ambiguous, unclear, or cut-off, do NOT guess. Output [CLARIFICATION_NEEDED] followed by your question."

            prompt_part = Part.from_text(prompt_text)

            # Generate analysis
            response = self.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
=======
        try:
            contents = [
                Content(role="user", parts=[Part.from_text(get_prompt('telegram_chat_prompt.md'))]),
                Content(role="model", parts=[Part.from_text("Understood. I'm ready to conduct the technical interview with appropriate sarcasm and depth.")])
            ]
            for msg in history:
                role = "user" if msg['role'] == 'user' else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg['content'])]))
            contents.append(Content(role="user", parts=[Part.from_text(user_message)]))
            return self.model.generate_content(contents).text
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I seem to be experiencing technical difficulties. How ironic."

    def analyze_multimodal(self, file_data: bytes, mime_type: str, filename: str) -> str:
        try:
            if mime_type.startswith(('image/', 'audio/', 'video/')) or mime_type == 'application/pdf':
                part = Part.from_data(data=file_data, mime_type=mime_type)
            else:
                return f"Unsupported file type: {mime_type}"
            prompt_part = Part.from_text(f"{get_prompt('multimodal_analysis_prompt.md')}\n\nFile: {filename}")
            return self.model.generate_content([prompt_part, part]).text
        except Exception as e:
            logger.error(f"Error analyzing multimodal: {e}")
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            return f"Error analyzing file: {str(e)}"


class RepositoryConfig:
<<<<<<< HEAD
    """Data class for repository configuration."""

    def __init__(self, name: str, label: str, token_env_var: str,
                 description: str = "", paths: Dict[str, str] = None):
        self.name = name  # "owner/repo"
        self.label = label  # "maestro", "beyond"
=======
    def __init__(self, name: str, label: str, token_env_var: str, description: str = "", paths: Dict[str, str] = None):
        self.name = name
        self.label = label
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        self.token_env_var = token_env_var
        self.description = description
        self.paths = paths or {}
        self._token = None
        self._github_client = None
        self._repo = None

    @property
    def token(self):
<<<<<<< HEAD
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
=======
        if self._token is None:
            self._token = os.environ.get(self.token_env_var)
            if not self._token: raise ValueError(f"Token not found for {self.token_env_var}")
        return self._token

    def get_github_client(self):
        if self._github_client is None: self._github_client = Github(self.token)
        return self._github_client

    def get_repo(self):
        if self._repo is None: self._repo = self.get_github_client().get_repo(self.name)
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        return self._repo


class GitHubConfigManager:
<<<<<<< HEAD
    """Manages repository configurations (Singleton)."""
    _instance = None

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'repos.json')

        self.config_path = config_path
        self.config_data = None
        self.repositories = {}  # label -> RepositoryConfig
=======
    _instance = None
    def __init__(self, config_path: str = None):
        if config_path is None: config_path = os.path.join(os.path.dirname(__file__), 'repos.json')
        self.config_path = config_path
        self.repositories = {}
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        self.routing_rules = {}
        self.default_repo_label = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: str = None):
<<<<<<< HEAD
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
=======
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
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
        except Exception as e:
            logger.error(f"Failed to load repository configuration: {e}")
            raise

<<<<<<< HEAD
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


def validate_repo_config():
    """Validate repository configuration and tokens."""
    missing_vars = []
    try:
        config_manager = GitHubConfigManager.get_instance()

        # Validate each repository has its token
        token_vars = set()
        for label, repo_config in config_manager.repositories.items():
            # Check for unique token env var names
            if repo_config.token_env_var in token_vars:
                logger.warning(f"Duplicate token_env_var '{repo_config.token_env_var}' found - this is allowed but not recommended")
            token_vars.add(repo_config.token_env_var)

            # Validate token exists
            token = os.environ.get(repo_config.token_env_var)
            if not token:
                missing_vars.append(f"{repo_config.token_env_var} (for {label})")

        if missing_vars:
            logger.error(f"CRITICAL: Missing repository tokens: {', '.join(missing_vars)}")
            logger.error("PR creation will fail for repositories with missing tokens")
        else:
            logger.info("All repository tokens are configured")

    except Exception as e:
        logger.error(f"Failed to validate repository configuration: {e}")


# Validate repository configuration now that classes are defined
validate_repo_config()


class TelegramClient:
    """Handles Telegram Bot API operations."""

    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TelegramClient initialization failed: TELEGRAM_BOT_TOKEN not set")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        try:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logger.info("Telegram Bot client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create Telegram Bot: {e}")
            raise

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """Escape special Markdown characters for Telegram."""
        # Escape Markdown special characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        escaped_text = text
        for char in special_chars:
            escaped_text = escaped_text.replace(char, f'\\{char}')
        return escaped_text

    @staticmethod
    def _sanitize_message(text: str, max_length: int = 4096) -> str:
        """Truncate message to Telegram's character limit."""
        if not text:
            return ""
        if len(text) > max_length:
            text = text[:max_length - 25]
            text += "\n\n... (message truncated)"
        return text

    @staticmethod
    def _prepare_message(text: str, parse_mode: Optional[str] = 'Markdown',
                         max_length: int = 4096) -> tuple:
        """Prepare message with automatic escaping and length validation.

        Returns: (safe_text, safe_parse_mode)
        """
        if not text:
            return ("", None)

        # Always truncate first
        safe_text = TelegramClient._sanitize_message(text, max_length)

        # Handle parse mode
        if parse_mode is None:
            return (safe_text, None)

        if parse_mode == 'Markdown':
            try:
                escaped = TelegramClient._escape_markdown(safe_text)
                return (escaped, 'Markdown')
            except Exception as e:
                logger.warning(f"Markdown escaping failed: {e}")
                return (safe_text, None)

        return (safe_text, parse_mode)

    def safe_send_error(self, chat_id: int, error: Exception, context: str = "") -> bool:
        """Safely send error message - always plain text."""
        error_text = str(error)
        message = f"❌ Error {context}:\n{error_text}" if context else f"❌ Error: {error_text}"
        safe_text, _ = TelegramClient._prepare_message(message, parse_mode=None, max_length=2000)
        return self.send_message(chat_id, safe_text, parse_mode=None)

    def safe_send_ai_content(self, chat_id: int, ai_text: str,
                             context: str = "AI Response", max_length: int = 3800) -> bool:
        """Safely send AI-generated content - always plain text."""
        if not ai_text:
            logger.warning(f"Empty {context} content to send")
            return True
        safe_text, _ = TelegramClient._prepare_message(ai_text, parse_mode=None, max_length=max_length)
        if len(ai_text) > max_length:
            logger.info(f"Truncated {context}: {len(ai_text)} -> {max_length} chars")
        return self.send_message(chat_id, safe_text, parse_mode=None)

    def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode: str = 'Markdown') -> bool:
        """Send a message to a Telegram chat using synchronous HTTP with safety checks.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Optional inline keyboard markup
            parse_mode: 'Markdown', 'HTML', or None (default: 'Markdown')
        """
        try:
            # Prepare message with all safety checks upfront
            safe_text, safe_parse_mode = TelegramClient._prepare_message(
                text, parse_mode, max_length=4096
            )

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

            # Prepare payload
            payload = {
                'chat_id': chat_id,
                'text': safe_text
            }

            if safe_parse_mode:
                payload['parse_mode'] = safe_parse_mode

            # Add reply markup if provided (for inline keyboards)
            if reply_markup:
                payload['reply_markup'] = reply_markup.to_json()

            # Attempt send with prepared mode
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    logger.info(f"Message sent to chat_id {chat_id} (mode: {safe_parse_mode or 'plain'})")
                    return True
                else:
                    logger.warning(f"Telegram API returned not ok: {result}")
                    # Fall through to retry without parse_mode
            except requests.RequestException as markdown_error:
                logger.warning(f"Failed to send with parse_mode={safe_parse_mode}: {markdown_error}")
                # Fall through to retry without parse_mode

            # Retry without parse_mode if first attempt failed and we had one
            if safe_parse_mode:
                logger.info("Retrying without parse_mode...")
                payload.pop('parse_mode', None)

                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    logger.info(f"Message sent to chat_id {chat_id} (plain text fallback)")
                    return True
                else:
                    logger.error(f"Failed to send message: {result}")
                    return False

            return False

        except requests.RequestException as e:
            logger.error(f"HTTP error sending message to Telegram: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to Telegram: {e}", exc_info=True)
            return False

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file from Telegram using file_id."""
        try:
            # Use synchronous HTTP requests instead of async to avoid event loop issues
            logger.info(f"Getting file path for file_id: {file_id}")

            # First, get the file path from Telegram
            get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            response = requests.get(get_file_url, timeout=10)
            response.raise_for_status()

            file_info = response.json()
            if not file_info.get('ok'):
                logger.error(f"getFile API returned not ok: {file_info}")
                return None

            file_path = file_info['result'].get('file_path')
            if not file_path:
                logger.error(f"No file_path in response: {file_info}")
                return None

            logger.info(f"File path retrieved: {file_path}")

            # Download the actual file
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            logger.info(f"Downloading from: {download_url[:80]}...")

            download_response = requests.get(download_url, timeout=30)
            download_response.raise_for_status()

            file_data = download_response.content
            logger.info(f"Downloaded file {file_id}, size: {len(file_data)} bytes")
            return file_data

        except requests.RequestException as e:
            logger.error(f"HTTP error downloading file from Telegram: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}", exc_info=True)
            return None

    def answer_callback_query(self, callback_query_id: str, text: str = None) -> bool:
        """Answer a callback query from inline keyboard using synchronous HTTP."""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"

            payload = {'callback_query_id': callback_query_id}
            if text:
                payload['text'] = text

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info(f"Answered callback query {callback_query_id}")
                return True
            else:
                logger.error(f"Failed to answer callback query: {result}")
                return False

        except requests.RequestException as e:
            logger.error(f"HTTP error answering callback query: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error answering callback query: {e}", exc_info=True)
            return False


class TelegramWebhookHandler:
    """Handles Telegram webhook events."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.github_manager = GitHubManager()
        self.telegram_client = TelegramClient()
        self.drive_client = GoogleDriveClient()

    def handle(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Telegram webhook."""
        try:
            # Check for callback query (inline button presses)
            callback_query = update_data.get('callback_query')
            if callback_query:
                return self._handle_callback_query(callback_query)

            # Parse Telegram Update object
            message = update_data.get('message', {})

            if not message:
                logger.warning("No message in update data")
                return {'status': 'ignored'}

            # Extract user and chat data
            from_user = message.get('from', {})
            chat = message.get('chat', {})

            user_id = from_user.get('id')
            username = from_user.get('username', 'unknown')
            first_name = from_user.get('first_name', '')
            chat_id = chat.get('id')

            # Extract message text or caption
            message_text = message.get('text', '').strip()

            # Generate session ID using Telegram user_id
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            session_id = f"telegram_{user_id}_{date_str}"

            logger.info(f"Processing message from user {username} (ID: {user_id}), chat_id: {chat_id}: {message_text}")

            # Handle commands
            if message_text.startswith('/start'):
                return self._handle_start_command(chat_id, first_name)

            elif message_text.startswith('/upload'):
                return self._handle_upload_request(session_id, chat_id)

            elif message_text.startswith('/done'):
                return self._handle_done_request(session_id, chat_id)

            elif message_text.startswith('/help'):
                return self._handle_help_command(chat_id)

            elif message_text.startswith('/logs'):
                return self._handle_logs_command(chat_id, user_id)

            # Handle file uploads (audio, images, documents)
            elif 'audio' in message or 'voice' in message or 'photo' in message or 'document' in message:
                return self._handle_file_upload(session_id, chat_id, message)

            # Handle regular text messages
            elif message_text:
                return self._handle_chat_message(session_id, chat_id, username, message_text)

            else:
                return {'status': 'ignored'}

        except Exception as e:
            logger.error(f"Error handling Telegram webhook: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    def _handle_start_command(self, chat_id: int, first_name: str) -> Dict[str, Any]:
        """Handle /start command."""
        welcome_text = f"👋 Hello {first_name}! I'm the V2V2B Interrogator.\n\n"
        welcome_text += "I'm a sarcastic but insightful Enterprise Architect here to extract architectural wisdom from you.\n\n"
        welcome_text += "**Commands:**\n"
        welcome_text += "/start - Show this welcome message\n"
        welcome_text += "/upload - Get upload link for audio/images\n"
        welcome_text += "/done - Complete session and create PR\n"
        welcome_text += "/logs - Fetch recent application logs\n"
        welcome_text += "/help - Show help information\n\n"
        welcome_text += "Just send me a message to start our technical interview!"

        self.telegram_client.send_message(chat_id, welcome_text)
        return {'status': 'ok'}

    def _handle_logs_command(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """Handle the /logs command to fetch and display application logs."""
        try:
            # Authorization check
            if LOGS_WHITELIST:
                whitelist = [int(uid.strip()) for uid in LOGS_WHITELIST.split(',')]
                if user_id not in whitelist:
                    self.telegram_client.send_message(chat_id, "❌ You are not authorized to use this command.")
                    return {'status': 'unauthorized'}

            self.telegram_client.send_message(chat_id, "⏳ Fetching logs for the last 5 minutes...")

            # Initialize logging client
            log_client = gcp_logging.Client(project=GCP_PROJECT)

            # Define filter
            function_name = os.environ.get('FUNCTION_NAME', 'v2v2b-interrogator')
            five_minutes_ago = (datetime.utcnow() - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            filter_str = (
                f'resource.type="cloud_function" '
                f'resource.labels.function_name="{function_name}" '
                f'severity>="ERROR" '
                f'timestamp>="{five_minutes_ago}"'
            )

            # Fetch logs
            entries = log_client.list_entries(filter_=filter_str, order_by=gcp_logging.DESCENDING)

            # Process and format logs
            log_summary = self._format_log_entries(entries)

            self.telegram_client.send_message(chat_id, log_summary, parse_mode='Markdown')
            return {'status': 'ok'}
        except Exception as e:
            logger.error(f"Error handling /logs command: {e}", exc_info=True)
            self.telegram_client.safe_send_error(chat_id, e, context="fetching logs")
            return {'status': 'error'}

    def _format_log_entries(self, entries) -> str:
        """Format log entries into a summary for Telegram."""
        log_count = 0
        error_count = 0
        critical_count = 0
        formatted_logs = []

        for entry in entries:
            log_count += 1
            if entry.severity == 'ERROR':
                error_count += 1
            elif entry.severity == 'CRITICAL':
                critical_count += 1

            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            payload = entry.payload if isinstance(entry.payload, str) else json.dumps(entry.payload)

            # Sanitize for Markdown
            payload = payload.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')

            formatted_logs.append(f"*{timestamp}* - `{entry.severity}`\n```{payload[:200]}...```")

        if log_count == 0:
            return "✅ No ERROR or CRITICAL logs found in the last 5 minutes."

        summary = (
            f"🔎 *Log Summary (Last 5 mins)*\n"
            f"----------------------------------\n"
            f"🔴 *Critical:* {critical_count}\n"
            f"🟠 *Errors:* {error_count}\n"
            f"----------------------------------\n\n"
            + "\n".join(formatted_logs[:10])  # Limit to 10 most recent logs
        )

        if log_count > 10:
            summary += "\n\n... (and more)"

        return summary

    def _handle_help_command(self, chat_id: int) -> Dict[str, Any]:
        """Handle /help command."""
        help_text = "**V2V2B Interrogator Help**\n\n"
        help_text += "I'm here to conduct technical interviews and extract architectural knowledge.\n\n"
        help_text += "**How to use:**\n"
        help_text += "1. Just send me text messages - I'll ask probing questions\n"
        help_text += "2. Upload .txt or .md files directly in Telegram\n"
        help_text += "3. Send MP4 videos for analysis\n"
        help_text += "4. Send voice recordings for transcription\n"
        help_text += "5. Use /done when finished to create a GitHub PR with our conversation\n\n"
        help_text += "**Features:**\n"
        help_text += "• Technical interview conversations\n"
        help_text += "• Text/Markdown file processing (.txt, .md)\n"
        help_text += "• Video analysis (MP4)\n"
        help_text += "• Voice recording transcription\n"
        help_text += "• Validation workflow - approve before saving\n"
        help_text += "• Automatic PR creation with session history\n"

        self.telegram_client.send_message(chat_id, help_text)
        return {'status': 'ok'}

    def _handle_upload_request(self, session_id: str, chat_id: int) -> Dict[str, Any]:
        """Handle /upload command."""
        # Save chat_id for this session
        FirestoreManager.save_message(session_id, 'system', 'Upload requested', str(chat_id))

        upload_url = f"{FUNCTION_URL}?mode=ui&session={session_id}"
        message = f"📎 Ready to upload? Click here:\n{upload_url}\n\n"
        message += "(Upload audio or images for analysis)\n\n"
        message += "💡 Tip: You can also send files directly in this Telegram chat!\n"
        message += "Supported: .txt, .md, .mp4, voice recordings"

        self.telegram_client.send_message(chat_id, message)
        return {'status': 'ok'}

    def _handle_done_request(self, session_id: str, chat_id: int) -> Dict[str, Any]:
        """Handle /done command - complete session or interviewer refinement."""
        try:
            # Check if interviewer mode is active
            if FirestoreManager.is_interviewer_active(session_id):
                return self._handle_interview_complete(session_id, chat_id)

            # Regular /done flow (create PR)
            history = FirestoreManager.get_session_history(session_id)

            if not history:
                self.telegram_client.send_message(chat_id, '❌ No session history found. Start chatting first!')
                return {'status': 'ok'}

            # Create PR
            pr_url = self.github_manager.create_pr_from_session(session_id, history)

            message = f'✅ Session complete! Pull request created:\n{pr_url}'
            self.telegram_client.send_message(chat_id, message)
            return {'status': 'ok'}
        except Exception as e:
            logger.error(f"Error handling /done request: {e}")
            self.telegram_client.safe_send_error(chat_id, e, context="creating PR")
            return {'status': 'error'}

    def _save_to_obsidian_drive(self, content: str, title: str, subfolder: str = "Interviews") -> Optional[str]:
        """Save markdown notes to Obsidian folder in Google Drive."""
        try:
            if not OBSIDIAN_DRIVE_FOLDER_ID:
                logger.warning("OBSIDIAN_DRIVE_FOLDER_ID not configured, cannot save to Obsidian")
                return None

            import re

            # Sanitize title for filename (remove invalid characters)
            title_clean = re.sub(r'[<>:"/\\|?*]', '', title or "Note").strip()

            # Generate filename with date prefix
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            filename = f"{date_str} - {title_clean}.md"

            # Add #Maestro tag if not present
            if "#Maestro" not in content:
                content = f"{content.rstrip()}\n\n#Maestro\n"

            # Upload to Google Drive Obsidian folder
            file_id = self.drive_client.upload_file(
                folder_id=OBSIDIAN_DRIVE_FOLDER_ID,
                filename=filename,
                content=content,
                mime_type='text/markdown'
            )

            if file_id:
                logger.info(f"✅ Saved to Obsidian Drive: {filename} (ID: {file_id})")
                return filename
            else:
                logger.error("Failed to upload to Google Drive")
                return None

        except Exception as e:
            logger.error(f"Error saving to Obsidian Drive: {e}", exc_info=True)
            return None

    def _handle_interview_complete(self, session_id: str, chat_id: int) -> Dict[str, Any]:
        """Finalize interviewer session and save refined notes to Obsidian."""
        try:
            self.telegram_client.send_message(chat_id, '⏳ Finalizing your notes...')

            # Get interviewer session data
            session = FirestoreManager.get_interviewer_session(session_id)
            if not session:
                self.telegram_client.send_message(chat_id, '❌ No active interview session found.')
                return {'status': 'error'}

            # Build context with all clarifications
            clarifications = session.get('clarifications', [])
            clarification_text = "\n\n".join([
                f"**Q:** {c['question']}\n**A:** {c['answer']}"
                for c in clarifications
            ])

            # Load interviewer prompt and generate final structured notes (Phase 3)
            interviewer_prompt = get_prompt("interviewer_prompt.md")
            finalization_message = f"""{interviewer_prompt}

**ORIGINAL TRANSCRIPT:**
{session['original_content']}

**ALL CLARIFICATIONS:**
{clarification_text}

PROCEED TO PHASE 3: FINALIZATION. Generate the complete structured notes in Obsidian-compatible markdown format with YAML frontmatter, following all requirements from the prompt."""

            # Generate final structured notes
            history = FirestoreManager.get_session_history(session_id)
            final_notes = self.gemini.chat_response(finalization_message, history)

            # Extract title from the notes
            title = self._extract_title_from_markdown(final_notes)

            # Save refined notes to Obsidian via Google Drive
            try:
                new_file_name = self._save_to_obsidian_drive(
                    content=final_notes,
                    title=title,
                    subfolder="Interviews"
                )

                if new_file_name:
                    logger.info(f"✅ Saved refined notes to Obsidian Drive: {new_file_name}")
                    new_file_path = new_file_name  # Store filename instead of Path
                else:
                    raise Exception("Failed to upload to Obsidian Drive")

            except Exception as obsidian_error:
                logger.error(f"Failed to save to Obsidian: {obsidian_error}")
                self.telegram_client.safe_send_error(chat_id, obsidian_error, context="saving notes to Obsidian")
                self.telegram_client.send_message(chat_id, "⚠️ Notes are saved in session history.", parse_mode=None)
                new_file_path = None

            # Tag source document with #MaestroProcessed
            if session.get('source_file_id'):
                # Google Drive source - update file
                try:
                    original_content = self.drive_client.download_file(session['source_file_id'])
                    if original_content:
                        tagged_content = self._add_processed_tag(original_content.decode('utf-8'))
                        self.drive_client.update_file_content(session['source_file_id'], tagged_content)
                        logger.info(f"Tagged source file in Drive: {session['source_file_id']}")
                except Exception as tag_error:
                    logger.error(f"Failed to tag source file: {tag_error}")
            else:
                # Telegram upload - save raw version to Obsidian
                if new_file_path:  # Only if Obsidian Drive is accessible
                    try:
                        raw_filename = self._save_to_obsidian_drive(
                            content=self._add_processed_tag(session['original_content']),
                            title=f"Raw - {title}",
                            subfolder="Raw Uploads"
                        )
                        if raw_filename:
                            logger.info(f"✅ Saved raw transcript: {raw_filename}")
                    except Exception as raw_error:
                        logger.error(f"Failed to save raw transcript: {raw_error}")

            # Extract and add action items to Kanban
            try:
                kanban_manager = KanbanManager(self.drive_client)
                kanban_manager._kanban_folder_id = KANBAN_FOLDER_ID

                action_items = kanban_manager.extract_action_items(final_notes, title)

                if action_items:
                    logger.info(f"Found {len(action_items)} action items to add to Kanban")
                    success = kanban_manager.update_kanban_board(action_items, title)

                    if success:
                        self.telegram_client.send_message(
                            chat_id,
                            f"📋 Added {len(action_items)} action items to Personal Kanban",
                            parse_mode=None
                        )
                    else:
                        logger.warning("Failed to update Kanban board")
                else:
                    logger.info("No action items found in interview notes")

            except Exception as kanban_error:
                logger.error(f"Error processing Kanban update: {kanban_error}", exc_info=True)
                # Don't fail interview flow - continue to PR creation

            # Create PR in beyond repository
            pr_url = None
            try:
                pr_url = self.github_manager.create_pr_from_interview(
                    title=title,
                    content=final_notes,
                    session_id=session_id,
                    repo_label='beyond',
                    target_path=None  # Let config determine the path
                )

                logger.info(f"✅ Created PR in beyond repo: {pr_url}")

                # Notify user about PR (use plain text to avoid Markdown escaping issues with URLs)
                self.telegram_client.send_message(
                    chat_id,
                    f"📝 PR created in beyond repository:\n{pr_url}",
                    parse_mode=None
                )

            except Exception as pr_error:
                logger.error(f"Failed to create PR in beyond repo: {pr_error}")
                # Don't fail the whole operation if PR fails
                self.telegram_client.send_message(
                    chat_id,
                    f"⚠️ Note: Failed to create PR in beyond repo, but notes are saved to Obsidian."
                )

            # Mark session as completed in Firebase
            FirestoreManager.complete_interviewer_session(
                session_id,
                refined_notes=final_notes,
                obsidian_path=str(new_file_path) if new_file_path else "Not saved to Obsidian"
            )

            # Generate and send summary (use plain text since it may contain URLs)
            summary = self._generate_summary(session, new_file_path, pr_url)
            self.telegram_client.send_message(chat_id, summary, parse_mode=None if pr_url else 'Markdown')

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error completing interview: {e}", exc_info=True)
            self.telegram_client.safe_send_error(chat_id, e, context="finalizing interview")
            return {'status': 'error'}

    def _add_processed_tag(self, content: str) -> str:
        """Add #MaestroProcessed tag to content if not present."""
        if "#MaestroProcessed" in content:
            return content
        return f"{content.rstrip()}\n\n#MaestroProcessed\n"

    def _extract_title_from_markdown(self, markdown: str) -> str:
        """Extract title from YAML frontmatter or first H1 heading."""
        import re

        # Try to extract from YAML frontmatter
        yaml_match = re.search(r'^---\s*\n.*?^title:\s*(.+?)$.*?^---', markdown, re.MULTILINE | re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip()

        # Try to find first H1 heading
        h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Fallback to date-based title
        return f"Interview {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

    def _generate_summary(self, session: Dict[str, Any], file_path: Optional[str], pr_url: Optional[str] = None) -> str:
        """Generate completion summary for user.

        If pr_url is provided, generates plain text version (no Markdown) to avoid URL escaping issues.
        Otherwise, uses Markdown formatting.
        """
        clarification_count = len(session.get('clarifications', []))

        # Use plain text if PR URL present (to avoid Markdown escaping issues)
        use_plain = pr_url is not None

        if use_plain:
            summary = "✅ Interview Complete!\n\n"

            if file_path:
                summary += f"📝 Refined Notes Saved\n"
                summary += f"   • File: {file_path}\n"
                summary += f"   • Location: Obsidian Google Drive\n\n"
            else:
                summary += "⚠️ Notes finalized but not saved to Obsidian\n\n"

            if pr_url:
                summary += f"🔀 Pull Request Created\n"
                summary += f"   • Repository: beyond\n"
                summary += f"   • URL: {pr_url}\n\n"

            summary += f"💬 Session Stats\n"
            summary += f"   • Clarifications: {clarification_count} rounds\n"
            summary += f"   • Source: {'Drive' if session.get('source_file_id') else 'Telegram upload'}\n"

            if session.get('source_file_id') or file_path:
                summary += f"\n🏷️ Tagged: #MaestroProcessed added to source\n"

            summary += f"\nYour structured notes are ready! 🎉"
        else:
            # Markdown version
            summary = "✅ *Interview Complete!*\n\n"

            if file_path:
                summary += f"📝 *Refined Notes Saved*\n"
                summary += f"   • File: `{file_path}`\n"
                summary += f"   • Location: Obsidian Google Drive\n\n"
            else:
                summary += "⚠️ *Notes finalized but not saved to Obsidian*\n\n"

            summary += f"💬 *Session Stats*\n"
            summary += f"   • Clarifications: {clarification_count} rounds\n"
            summary += f"   • Source: {'Drive' if session.get('source_file_id') else 'Telegram upload'}\n"

            if session.get('source_file_id') or file_path:
                summary += f"\n🏷️ *Tagged*: #MaestroProcessed added to source\n"

            summary += f"\nYour structured notes are ready! 🎉"

        return summary

    def _handle_file_upload(self, session_id: str, chat_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file uploads via Telegram (audio, voice, photo, document, video)."""
        try:
            # Determine file type and process accordingly
            if 'voice' in message:
                return self._process_voice_message(session_id, chat_id, message['voice'])
            elif 'video' in message:
                video = message['video']
                if video.get('mime_type') == 'video/mp4':
                    return self._process_video_file(session_id, chat_id, video)
                else:
                    self.telegram_client.send_message(chat_id, '❌ Only MP4 videos are supported.')
                    return {'status': 'error'}
            elif 'document' in message:
                document = message['document']
                mime_type = document.get('mime_type', '')
                filename = document.get('file_name', '')

                # Support .txt, .md, and .pdf files
                if (mime_type in ['text/plain', 'text/markdown', 'application/pdf'] or
                    filename.endswith('.txt') or filename.endswith('.md') or filename.endswith('.pdf')):

                    # Route to appropriate handler based on file type
                    if mime_type == 'application/pdf' or filename.endswith('.pdf'):
                        return self._process_pdf_file(session_id, chat_id, document)
                    else:
                        return self._process_text_file(session_id, chat_id, document)
                else:
                    self.telegram_client.send_message(chat_id, '❌ Only .txt, .md, and .pdf files are supported for documents.')
                    return {'status': 'error'}
            elif 'photo' in message:
                # Process images (Archivist Loop)
                return self._process_image_file(session_id, chat_id, message['photo'])
            elif 'audio' in message:
                # Redirect audio to web UI (can be extended later)
                info_text = "📎 For audio files, please use the web interface:\n"
                info_text += f"{FUNCTION_URL}?mode=ui&session={session_id}"
                self.telegram_client.send_message(chat_id, info_text)
                return {'status': 'ok'}
            else:
                return {'status': 'ignored'}

        except Exception as e:
            logger.error(f"Error handling file upload: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing file: {str(e)}')
            return {'status': 'error'}

    def _process_text_file(self, session_id: str, chat_id: int, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded text file."""
        try:
            file_id = document['file_id']
            filename = document.get('file_name', 'document.txt')
            mime_type = document.get('mime_type', 'unknown')
            file_size = document.get('file_size', 0)

            logger.info(f"Processing text file: {filename}, MIME: {mime_type}, Size: {file_size}, FileID: {file_id}")
            clean_filename = filename[:100]  # Truncate long names
            self.telegram_client.send_message(chat_id, f'📄 Processing text file: {clean_filename}...', parse_mode=None)

            # Download file
            logger.info(f"Attempting to download file {file_id}")
            try:
                file_data = self.telegram_client.download_file(file_id)
            except Exception as download_error:
                logger.error(f"Exception during download: {download_error}", exc_info=True)
                self.telegram_client.safe_send_error(chat_id, download_error, context="downloading file")
                self.telegram_client.send_message(chat_id, "Please contact support.", parse_mode=None)
                return {'status': 'error'}

            if not file_data:
                logger.error(f"Download returned None for file {file_id}")
                self.telegram_client.send_message(
                    chat_id,
                    f'❌ Failed to download file.\n\nFile ID: {file_id}\nFilename: {clean_filename}\n\nThe download returned empty. Please try again or contact support.',
                    parse_mode=None
                )
                return {'status': 'error'}

            logger.info(f"Successfully downloaded {len(file_data)} bytes for {filename}")
            self.telegram_client.send_message(chat_id, f'✅ Downloaded {len(file_data)} bytes. Analyzing...')

            # Decode text content
            try:
                content = file_data.decode('utf-8')
            except UnicodeDecodeError:
                content = file_data.decode('latin-1')  # Fallback encoding

            # Activate interviewer mode for transcript refinement
            FirestoreManager.create_interviewer_session(
                session_id=session_id,
                source_file_id=None,  # Telegram upload, no Drive source
                source_file_path=None,
                original_content=content
            )

            # Load interviewer prompt and analyze transcript
            interviewer_prompt = get_prompt("interviewer_prompt.md")
            initial_message = f"{interviewer_prompt}\n\n**TRANSCRIPT TO ANALYZE:**\n\n{content}"

            # Generate initial clarifying questions
            initial_questions = self.gemini.chat_response(initial_message, [])

            # Save initial bot message to session history
            FirestoreManager.save_message(session_id, 'assistant', initial_questions, str(chat_id))

            # Send questions to user
            self.telegram_client.send_message(chat_id, "📝 Transcript Analysis Started\n", parse_mode=None)
            self.telegram_client.safe_send_ai_content(chat_id, initial_questions, context="Interview Questions")
            self.telegram_client.send_message(chat_id, "Type your answers or '/DONE' when ready to finalize.", parse_mode=None)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing text file: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing text file: {str(e)}')
            return {'status': 'error'}

    def _process_pdf_file(self, session_id: str, chat_id: int, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded PDF document."""
        try:
            file_id = document['file_id']
            filename = document.get('file_name', 'document.pdf')
            file_size = document.get('file_size', 0)

            # Gemini has a 15MB limit for PDFs
            MAX_PDF_SIZE = 15 * 1024 * 1024  # 15 MB

            logger.info(f"Processing PDF: {filename}, Size: {file_size}, FileID: {file_id}")

            if file_size > MAX_PDF_SIZE:
                self.telegram_client.send_message(
                    chat_id,
                    f'❌ PDF file too large.\n\nMaximum size: 15 MB\nYour file: {file_size / 1024 / 1024:.1f} MB\n\nPlease compress or split the PDF.'
                )
                return {'status': 'error'}

            self.telegram_client.send_message(chat_id, f'📄 Processing PDF: *{filename}*...')

            # Download PDF file
            logger.info(f"Attempting to download PDF {file_id}")
            try:
                file_data = self.telegram_client.download_file(file_id)
            except Exception as download_error:
                logger.error(f"Exception during PDF download: {download_error}", exc_info=True)
                self.telegram_client.send_message(
                    chat_id,
                    f'❌ Failed to download PDF.\n\nError: {str(download_error)}\n\nPlease try again or contact support.'
                )
                return {'status': 'error'}

            if not file_data:
                logger.error(f"PDF download returned None for file {file_id}")
                self.telegram_client.send_message(
                    chat_id,
                    f'❌ Failed to download PDF.\n\nFile ID: `{file_id}`\nFilename: `{filename}`\n\nThe download returned empty. Please try again.'
                )
                return {'status': 'error'}

            logger.info(f"Successfully downloaded {len(file_data)} bytes for {filename}")
            self.telegram_client.send_message(chat_id, f'✅ Downloaded. Analyzing PDF with Gemini...')

            # Analyze PDF with Gemini multimodal (extracts text, images, tables, charts)
            analysis = self.gemini.analyze_multimodal(file_data, 'application/pdf', filename)

            # Activate interviewer mode for PDF content refinement
            FirestoreManager.create_interviewer_session(
                session_id=session_id,
                source_file_id=None,  # Telegram upload, no Drive source
                source_file_path=None,
                original_content=analysis
            )

            # Load interviewer prompt and analyze content
            interviewer_prompt = get_prompt("interviewer_prompt.md")
            initial_message = f"{interviewer_prompt}\n\n**PDF DOCUMENT ANALYSIS:**\n\n{analysis}"

            # Generate initial clarifying questions
            initial_questions = self.gemini.chat_response(initial_message, [])

            # Save initial bot message to session history
            FirestoreManager.save_message(session_id, 'assistant', initial_questions, str(chat_id))

            # Send questions to user
            self.telegram_client.send_message(chat_id, "📝 PDF Analysis Started\n", parse_mode=None)
            self.telegram_client.safe_send_ai_content(chat_id, initial_questions, context="PDF Interview Questions")
            self.telegram_client.send_message(chat_id, "Type your answers or '/DONE' when ready to finalize.", parse_mode=None)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing PDF: {str(e)}')
            return {'status': 'error'}

    def _process_image_file(self, session_id: str, chat_id: int, photos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process uploaded image file (Archivist Loop)."""
        try:
            # Get the largest photo (last in list)
            photo = photos[-1]
            file_id = photo['file_id']
            filename = f"image_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jpg"
            file_size = photo.get('file_size', 0)

            logger.info(f"Processing image: {filename}, Size: {file_size}, FileID: {file_id}")
            self.telegram_client.send_message(chat_id, f'🖼️ Analyzing image with Archivist persona...')

            # Download image
            file_data = self.telegram_client.download_file(file_id)
            if not file_data:
                self.telegram_client.send_message(chat_id, '❌ Failed to download image.')
                return {'status': 'error'}

            # Analyze with Gemini (multimodal)
            analysis = self.gemini.analyze_multimodal(file_data, 'image/jpeg', filename)

            # Check for clarification request
            if '[CLARIFICATION_NEEDED]' in analysis:
                # Extract the question (everything after the token)
                parts = analysis.split('[CLARIFICATION_NEEDED]', 1)
                pre_context = parts[0]
                question = parts[1].strip()

                # Activate interviewer mode for clarification
                # We store the initial analysis + context in 'original_content'
                FirestoreManager.create_interviewer_session(
                    session_id=session_id,
                    source_file_id=file_id, # Track Telegram file ID
                    source_file_path=None,
                    original_content=f"Image Analysis Context:\n{pre_context}\n\nClarification Question:\n{question}"
                )

                # Save the system question to history
                FirestoreManager.save_message(session_id, 'assistant', f"[CLARIFICATION REQUEST] {question}", str(chat_id))

                # Send warning/question to user
                warning_msg = f"⚠️ **CLARIFICATION NEEDED**\n\nThe Archivist needs your help:\n_{question}_"
                self.telegram_client.send_message(chat_id, warning_msg)
                self.telegram_client.send_message(chat_id, "Please reply with your answer, or type /done to skip.")

                return {'status': 'ok'}

            # No clarification needed - proceed to structure notes
            # Generate structured notes
            structured_notes = self._generate_structured_notes(analysis, filename, 'image')

            # Create validation ID
            validation_id = f"{session_id}_{file_id}"

            # Save to pending validations
            FirestoreManager.save_pending_validation(
                validation_id=validation_id,
                session_id=session_id,
                chat_id=chat_id,
                file_type='image',
                filename=filename,
                content=analysis,
                structured_notes=structured_notes,
                file_data=file_data
            )

            # Send preview with validation buttons
            self._send_validation_prompt(chat_id, filename, structured_notes, validation_id)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing image file: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing image: {str(e)}')
            return {'status': 'error'}

    def _process_video_file(self, session_id: str, chat_id: int, video: Dict[str, Any]) -> Dict[str, Any]:
        """Process uploaded MP4 video file."""
        try:
            file_id = video['file_id']
            filename = video.get('file_name', 'video.mp4')

            self.telegram_client.send_message(chat_id, f'🎥 Processing video: *{filename}*...')

            # Download video
            file_data = self.telegram_client.download_file(file_id)
            if not file_data:
                self.telegram_client.send_message(chat_id, '❌ Failed to download video.')
                return {'status': 'error'}

            # Analyze with Gemini (multimodal supports video)
            analysis = self.gemini.analyze_multimodal(file_data, 'video/mp4', filename)

            # Generate structured notes
            structured_notes = self._generate_structured_notes(analysis, filename, 'video')

            # Create validation ID
            validation_id = f"{session_id}_{file_id}"

            # Save to pending validations (store file data for later indexing)
            FirestoreManager.save_pending_validation(
                validation_id=validation_id,
                session_id=session_id,
                chat_id=chat_id,
                file_type='video',
                filename=filename,
                content=analysis,
                structured_notes=structured_notes,
                file_data=file_data
            )

            # Send preview with validation buttons
            self._send_validation_prompt(chat_id, filename, structured_notes, validation_id)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing video file: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing video: {str(e)}')
            return {'status': 'error'}

    def _process_voice_message(self, session_id: str, chat_id: int, voice: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegram voice recording."""
        try:
            file_id = voice['file_id']
            duration = voice.get('duration', 0)
            filename = f"voice_recording_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.ogg"

            self.telegram_client.send_message(chat_id, f'🎤 Processing voice recording ({duration}s)...')

            # Download voice file
            file_data = self.telegram_client.download_file(file_id)
            if not file_data:
                self.telegram_client.send_message(chat_id, '❌ Failed to download voice recording.')
                return {'status': 'error'}

            # Transcribe and analyze with Gemini (audio/ogg format)
            transcript = self.gemini.analyze_multimodal(file_data, 'audio/ogg', filename)

            # Activate interviewer mode for transcript refinement
            FirestoreManager.create_interviewer_session(
                session_id=session_id,
                source_file_id=None,  # Telegram upload, no Drive source
                source_file_path=None,
                original_content=transcript
            )

            # Load interviewer prompt and analyze transcript
            interviewer_prompt = get_prompt("interviewer_prompt.md")
            initial_message = f"{interviewer_prompt}\n\n**TRANSCRIPT TO ANALYZE:**\n\n{transcript}"

            # Generate initial clarifying questions
            initial_questions = self.gemini.chat_response(initial_message, [])

            # Save initial bot message to session history
            FirestoreManager.save_message(session_id, 'assistant', initial_questions, str(chat_id))

            # Send questions to user
            self.telegram_client.send_message(chat_id, "📝 Voice Transcript Analysis Started\n", parse_mode=None)
            self.telegram_client.safe_send_ai_content(chat_id, initial_questions, context="Voice Interview Questions")
            self.telegram_client.send_message(chat_id, "Type your answers or '/DONE' when ready to finalize.", parse_mode=None)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing voice recording: {e}", exc_info=True)
            self.telegram_client.safe_send_error(chat_id, e, context="processing voice recording")
            return {'status': 'error'}

    def _generate_structured_notes(self, content: str, filename: str, file_type: str) -> str:
        """Generate structured notes from file content using Gemini."""
        try:
            validation_prompt = get_prompt('file_validation_prompt.md')

            prompt = f"{validation_prompt}\n\n"
            prompt += f"## File Information\n"
            prompt += f"- **Filename:** {filename}\n"
            prompt += f"- **Type:** {file_type}\n\n"
            prompt += f"## Content to Analyze:\n\n{content}"

            # Use Gemini to generate structured notes
            structured_notes = self.gemini.model.generate_content(prompt).text

            return structured_notes

        except Exception as e:
            logger.error(f"Error generating structured notes: {e}")
            # Fallback to basic formatting
            return f"# {filename}\n\n## Content\n\n{content}\n\n## Tags\n#upload #{file_type}"

    def _send_validation_prompt(self, chat_id: int, filename: str, structured_notes: str, validation_id: str) -> None:
        """Send validation prompt with inline keyboard."""
        try:
            # Truncate notes if too long for Telegram message (4096 char limit)
            # Leave room for header and footer
            max_length = 3800
            preview = structured_notes[:max_length]
            if len(structured_notes) > max_length:
                preview += "\n\n... (truncated for preview)"

            # Send header message separately to avoid Markdown issues with user content
            header = f"📋 Preview of structured notes for: {filename}\n"
            header += "━" * 40 + "\n"
            self.telegram_client.send_message(chat_id, header)

            # Send the structured notes as plain text (no Markdown parsing of user content)
            # This avoids issues with unescaped Markdown in generated notes
            self.telegram_client.send_message(chat_id, preview, parse_mode=None)

            # Send footer with validation request
            footer = "━" * 40 + "\n"
            footer += "Please validate this content:"

            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Validate & Save", callback_data=f"validate:{validation_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject:{validation_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            self.telegram_client.send_message(chat_id, footer, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error sending validation prompt: {e}", exc_info=True)
            raise

    def _handle_callback_query(self, callback_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle inline button callback queries."""
        try:
            query_id = callback_query['id']
            data = callback_query['data']
            from_user = callback_query.get('from', {})
            user_id = from_user.get('id')

            # Get chat_id from message
            message = callback_query.get('message', {})
            chat = message.get('chat', {})
            chat_id = chat.get('id')

            logger.info(f"Processing callback query from user {user_id}: {data}")

            # Parse callback data (format: "action:validation_id")
            parts = data.split(':', 1)
            if len(parts) != 2:
                logger.error(f"Invalid callback data format: {data}")
                return {'status': 'error'}

            action, validation_id = parts

            # Retrieve pending validation
            pending = FirestoreManager.get_pending_validation(validation_id)
            if not pending:
                self.telegram_client.answer_callback_query(query_id, "❌ Validation expired or not found")
                self.telegram_client.send_message(chat_id, "❌ Validation not found. It may have expired.")
                return {'status': 'error'}

            if action == 'validate':
                return self._handle_validation_approve(query_id, chat_id, pending)
            elif action == 'reject':
                return self._handle_validation_reject(query_id, chat_id, pending)
            else:
                logger.error(f"Unknown callback action: {action}")
                return {'status': 'error'}

        except Exception as e:
            logger.error(f"Error handling callback query: {e}", exc_info=True)
            return {'status': 'error'}

    def _handle_validation_approve(self, query_id: str, chat_id: int, pending: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation approval - save to knowledge base."""
        try:
            validation_id = pending['validation_id']
            session_id = pending['session_id']
            filename = pending['filename']
            structured_notes = pending['structured_notes']
            content = pending['content']

            # Answer the callback query
            self.telegram_client.answer_callback_query(query_id, "✅ Validating and saving...")

            # Send processing message
            self.telegram_client.send_message(chat_id, f"✅ *Validation approved!*\n\nSaving `{filename}` to knowledge base...")

            # Index in knowledge base
            kb_manager = KnowledgeBaseManager()
            file_id = f"telegram_{validation_id}"

            # Generate summary for indexing (first paragraph of structured notes)
            summary_lines = structured_notes.split('\n\n')[:2]
            summary = '\n'.join(summary_lines)

            kb_manager.index_transcript(
                file_id=file_id,
                filename=filename,
                content=content,
                summary=summary,
                metadata={
                    'source': 'telegram',
                    'session_id': session_id,
                    'structured_notes': structured_notes,
                    'validated_at': datetime.utcnow().isoformat()
                }
            )

            # Save to session history
            FirestoreManager.save_message(
                session_id,
                'assistant',
                f"[VALIDATED FILE: {filename}]\n\n{structured_notes}",
                str(chat_id)
            )

            # Delete pending validation
            FirestoreManager.delete_pending_validation(validation_id)

            # Send success message
            success_msg = f"✅ *Successfully saved!*\n\n"
            success_msg += f"📁 File: `{filename}`\n"
            success_msg += f"💾 Indexed in knowledge base\n"
            success_msg += f"📝 Added to session history\n\n"
            success_msg += f"Use /done to create a PR with this session."

            self.telegram_client.send_message(chat_id, success_msg)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error approving validation: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error saving file: {str(e)}')
            return {'status': 'error'}

    def _handle_validation_reject(self, query_id: str, chat_id: int, pending: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation rejection - delete pending upload."""
        try:
            validation_id = pending['validation_id']
            filename = pending['filename']

            # Answer the callback query
            self.telegram_client.answer_callback_query(query_id, "❌ Rejected")

            # Delete pending validation
            FirestoreManager.delete_pending_validation(validation_id)

            # Send confirmation
            reject_msg = f"❌ *Rejected and deleted*\n\n"
            reject_msg += f"File `{filename}` was not saved.\n"
            reject_msg += f"You can upload a different file if needed."

            self.telegram_client.send_message(chat_id, reject_msg)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error rejecting validation: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error rejecting file: {str(e)}')
            return {'status': 'error'}

    def _handle_interviewer_response(self, session_id: str, chat_id: int, user_response: str) -> Dict[str, Any]:
        """Handle user responses during interviewer mode."""
        try:
            # Get interviewer session
            session = FirestoreManager.get_interviewer_session(session_id)
            if not session:
                logger.error(f"Interviewer session not found: {session_id}")
                return {'status': 'error'}

            # Save user message to regular session history
            FirestoreManager.save_message(session_id, 'user', user_response, str(chat_id))

            # Get the last assistant question from session history
            history = FirestoreManager.get_session_history(session_id)
            last_question = ""
            if len(history) >= 1:
                for msg in reversed(history):
                    if msg.get('role') == 'assistant':
                        last_question = msg.get('content', '')
                        break

            # Add clarification to interviewer session
            FirestoreManager.add_clarification(session_id, last_question, user_response)

            # Build context with all clarifications
            clarifications = session.get('clarifications', [])
            clarification_text = "\n\n".join([
                f"**Q:** {c['question']}\n**A:** {c['answer']}"
                for c in clarifications
            ])

            # Load interviewer prompt and generate next question
            interviewer_prompt = get_prompt("interviewer_prompt.md")
            context_message = f"""{interviewer_prompt}

**ORIGINAL TRANSCRIPT:**
{session['original_content']}

**CLARIFICATIONS SO FAR:**
{clarification_text}

**USER'S LATEST RESPONSE:**
{user_response}

Continue the interview process. Ask follow-up clarifying questions if needed, or indicate if you have enough information to proceed to finalization."""

            # Generate next question or confirmation
            next_response = self.gemini.chat_response(context_message, history)

            # Save bot response
            FirestoreManager.save_message(session_id, 'assistant', next_response, str(chat_id))

            # Send to user
            self.telegram_client.send_message(
                chat_id,
                f"{next_response}\n\n_Type your answer or '/DONE' to finalize the notes._"
            )

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error handling interviewer response: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, '❌ Error processing your response. Please try again.')
            return {'status': 'error'}

    def _handle_chat_message(self, session_id: str, chat_id: int, username: str, message_text: str) -> Dict[str, Any]:
        """Handle regular chat message."""
        try:
            # Check if interviewer mode is active
            if FirestoreManager.is_interviewer_active(session_id):
                return self._handle_interviewer_response(session_id, chat_id, message_text)

            # Regular chat flow
            # Save user message (use chat_id as space_name)
            FirestoreManager.save_message(session_id, 'user', message_text, str(chat_id))

            # Get history
            history = FirestoreManager.get_session_history(session_id)

            # Generate response
            bot_response = self.gemini.chat_response(message_text, history)

            # Save bot response
            FirestoreManager.save_message(session_id, 'assistant', bot_response, str(chat_id))

            # Send response via Telegram (AI content - use safe method)
            self.telegram_client.safe_send_ai_content(chat_id, bot_response, context="Chat Response", max_length=3800)

            return {'status': 'ok'}
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            self.telegram_client.send_message(chat_id, '❌ Sorry, I encountered an error processing your message.', parse_mode=None)
            return {'status': 'error'}


class UploadHandler:
    """Handles file upload processing."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.telegram_client = TelegramClient()

    def handle(self, session_id: str, file_data: bytes, filename: str, content_type: str) -> str:
        """Process uploaded file."""
        try:
            logger.info(f"Processing upload for session {session_id}: {filename} ({content_type})")

            # Check file size for PDFs (15 MB limit for Gemini)
            if content_type == 'application/pdf' and len(file_data) > 15 * 1024 * 1024:
                return self._error_html('PDF too large. Maximum size is 15 MB.')

            # Analyze file with Gemini
=======
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
    """Handles GitHub operations."""
    def __init__(self, config_path: str = None):
        self.config_manager = GitHubConfigManager.get_instance(config_path)

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


class SyncTelegramClient:
    """
    Handles Telegram Bot API operations using synchronous requests.
    Used for HTTP handlers (Upload UI) where async context is not available/needed.
    """
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
                 # Retry without parse mode
                 payload.pop('parse_mode')
                 response = requests.post(url, json=payload, timeout=10)

            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"SyncTelegramClient error: {e}")
            return False


# --------------------------------------------------------------------------------
# NEW FEATURE: GCP Log Fetching
# --------------------------------------------------------------------------------
def fetch_gcp_logs(function_name: str) -> List[str]:
    """Fetches recent logs for the specified Cloud Function within the last 5 minutes."""
    try:
        client = cloud_logging.Client()
        five_mins_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"

        # Filter for the specific function and time range
        filter_str = (
            f'resource.type="cloud_function" AND '
            f'resource.labels.function_name="{function_name}" AND '
            f'timestamp >= "{five_mins_ago}"'
        )

        entries = client.list_entries(filter_=filter_str, order_by=cloud_logging.DESCENDING, page_size=50)

        logs = []
        count = 0
        for entry in entries:
            if count >= 50: break

            timestamp = entry.timestamp.isoformat() if entry.timestamp else "Unknown"
            severity = entry.severity or "INFO"
            payload = entry.payload

            if isinstance(payload, dict):
                message = json.dumps(payload)
            else:
                message = str(payload)

            logs.append(f"[{timestamp}] {severity}: {message}")
            count += 1

        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise


async def logs_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram handler for /logs command."""
    try:
        await update.message.reply_text("🔍 Fetching logs from GCP...")

        # Run blocking GCP call in executor
        loop = asyncio.get_running_loop()
        logs = await loop.run_in_executor(None, fetch_gcp_logs, TARGET_FUNCTION_NAME)

        if not logs:
            await update.message.reply_text("No logs found in the last 5 minutes.")
            return

        # Format logs
        log_text = "\n".join(logs)
        if len(log_text) > 4000:
            log_text = log_text[:3900] + "\n... (truncated)"

        message = f"```\n{log_text}\n```"
        await update.message.reply_markdown_v2(message)

    except Exception as e:
        error_msg = f"Log retrieval failed: {str(e)}. Check the function's IAM permissions."
        await update.message.reply_text(error_msg)


# --------------------------------------------------------------------------------
# REFACTORED BOT HANDLERS (Async)
# --------------------------------------------------------------------------------
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
            "/logs - Fetch recent logs from Target GCF\n"
            "/done - Complete session and create PR\n"
            "/help - Show help information\n\n"
            "Just send me a message to start our technical interview!"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "**V2V2B Interrogator Help**\n\n"
            "I'm here to conduct technical interviews and extract architectural knowledge.\n\n"
            "**How to use:**\n"
            "1. Send text messages - I'll ask probing questions\n"
            "2. Upload .txt, .md, .pdf files directly\n"
            "3. Send voice recordings for transcription\n"
            "4. Use /logs to see system logs\n"
            "5. Use /done when finished to create a GitHub PR\n"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        # Save chat_id mapping
        # Note: We use run_in_executor for Firestore writes to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'system', 'Upload requested', str(update.effective_chat.id))

        upload_url = f"{FUNCTION_URL}?mode=ui&session={session_id}"
        message = (
            f"📎 Ready to upload? Click here:\n{upload_url}\n\n"
            "(Upload audio or images for analysis)\n\n"
            "💡 Tip: You can also send files directly in this Telegram chat!"
        )
        await update.message.reply_text(message)

    async def done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session_id = f"telegram_{update.effective_user.id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        loop = asyncio.get_running_loop()

        try:
            # Check interviewer mode
            is_active = await loop.run_in_executor(None, FirestoreManager.is_interviewer_active, session_id)

            if is_active:
                await self._handle_interview_complete(update, context, session_id)
            else:
                # Regular session done
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                if not history:
                    await update.message.reply_text('❌ No session history found. Start chatting first!')
                    return

                pr_url = await loop.run_in_executor(None, self.github_manager.create_pr_from_session, session_id, history)
                await update.message.reply_text(f'✅ Session complete! Pull request created:\n{pr_url}')

        except Exception as e:
            logger.error(f"Error in done handler: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def _handle_interview_complete(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str):
        await update.message.reply_text('⏳ Finalizing your notes...')
        loop = asyncio.get_running_loop()

        try:
            session = await loop.run_in_executor(None, FirestoreManager.get_interviewer_session, session_id)
            if not session:
                await update.message.reply_text('❌ No active interview session found.')
                return

            # Build context
            clarifications = session.get('clarifications', [])
            clarification_text = "\n\n".join([f"**Q:** {c['question']}\n**A:** {c['answer']}" for c in clarifications])

            interviewer_prompt = get_prompt("interviewer_prompt.md")
            finalization_msg = f"{interviewer_prompt}\n\n**ORIGINAL TRANSCRIPT:**\n{session['original_content']}\n\n**CLARIFICATIONS:**\n{clarification_text}\n\nPROCEED TO PHASE 3: FINALIZATION."

            history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
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
            await loop.run_in_executor(None, FirestoreManager.complete_interviewer_session, session_id, final_notes, str(new_file_name))
            await update.message.reply_text("✅ Interview Complete! Notes finalized.")

        except Exception as e:
            logger.error(f"Interview completion failed: {e}")
            await update.message.reply_text(f"❌ Error finalizing interview: {e}")

    def _extract_title(self, text: str) -> str:
        import re
        match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else f"Interview {datetime.utcnow().strftime('%Y-%m-%d')}"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        if not update.message or not update.message.text: return

        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        text = update.message.text
        loop = asyncio.get_running_loop()

        try:
            # Check for active interview
            is_active = await loop.run_in_executor(None, FirestoreManager.is_interviewer_active, session_id)

            if is_active:
                # Interviewer flow
                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'user', text, str(update.effective_chat.id))

                # Get last question
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                last_q = ""
                for msg in reversed(history):
                    if msg.get('role') == 'assistant':
                        last_q = msg.get('content', '')
                        break

                await loop.run_in_executor(None, FirestoreManager.add_clarification, session_id, last_q, text)

                # Generate next question
                session = await loop.run_in_executor(None, FirestoreManager.get_interviewer_session, session_id)
                clarifications = session.get('clarifications', [])
                clar_text = "\n".join([f"Q: {c['question']}\nA: {c['answer']}" for c in clarifications])

                prompt = f"{get_prompt('interviewer_prompt.md')}\n\nTranscript: {session['original_content']}\n\nClarifications:\n{clar_text}\n\nUser: {text}\n\nContinue interview."
                response = await loop.run_in_executor(None, self.gemini.chat_response, prompt, history)

                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', response, str(update.effective_chat.id))
                await update.message.reply_text(response)

            else:
                # Regular chat flow
                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'user', text, str(update.effective_chat.id))
                history = await loop.run_in_executor(None, FirestoreManager.get_session_history, session_id)
                response = await loop.run_in_executor(None, self.gemini.chat_response, text, history)

                await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', response, str(update.effective_chat.id))
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Error processing message.")

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads."""
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

            # Analyze
            analysis = ""
            if mime_type == 'application/pdf' or filename.endswith('.pdf'):
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
            await loop.run_in_executor(None, FirestoreManager.create_interviewer_session, session_id, None, None, analysis)

            # Generate initial questions
            prompt = f"{get_prompt('interviewer_prompt.md')}\n\nTRANSCRIPT:\n{analysis}"
            questions = await loop.run_in_executor(None, self.gemini.chat_response, prompt, [])

            await loop.run_in_executor(None, FirestoreManager.save_message, session_id, 'assistant', questions, str(update.effective_chat.id))

            await update.message.reply_text(f"📝 Analysis Complete. Starting interview:\n\n{questions}")

        except Exception as e:
            logger.error(f"File handler error: {e}")
            await update.message.reply_text(f"❌ Error processing file: {e}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks (if any)."""
        query = update.callback_query
        await query.answer()
        # (Validation logic omitted for brevity in this refactor, but structure is here)
        await query.edit_message_text(text=f"Selected option: {query.data}")


def init_bot() -> Application:
    """Initializes the Telegram Application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    handlers = BotHandlers()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("upload", handlers.upload))
    application.add_handler(CommandHandler("done", handlers.done))
    application.add_handler(CommandHandler("logs", logs_command_handler))

    application.add_handler(MessageHandler(filters.ATTACHMENT | filters.VOICE, handlers.handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    application.add_handler(CallbackQueryHandler(handlers.handle_callback))

    return application


class UploadHandler:
    """Handles file upload processing via HTTP (uses SyncTelegramClient)."""
    def __init__(self):
        self.gemini = GeminiClient()
        self.telegram_client = SyncTelegramClient()

    def handle(self, session_id: str, file_data: bytes, filename: str, content_type: str) -> str:
        try:
            if content_type == 'application/pdf' and len(file_data) > 15 * 1024 * 1024:
                return self._error_html('PDF too large. Max 15 MB.')

>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            if content_type in ['application/pdf', 'audio/*', 'image/*', 'video/*'] or content_type.startswith(('audio/', 'image/', 'video/')):
                analysis = self.gemini.analyze_multimodal(file_data, content_type, filename)
            elif content_type == 'text/plain' or filename.endswith(('.txt', '.md')):
                analysis = file_data.decode('utf-8')
            else:
                return self._error_html(f'Unsupported file type: {content_type}')

<<<<<<< HEAD
            # Save to Firestore
            FirestoreManager.save_message(
                session_id,
                'assistant',
                f"[FILE ANALYSIS: {filename}]\n\n{analysis}"
            )

            # Get chat_id from space_name (stored as string) and send message back to Telegram
            chat_id_str = FirestoreManager.get_space_name(session_id)
            if chat_id_str:
                try:
                    chat_id = int(chat_id_str)
                    message = f"📎 File analyzed: *{filename}*\n\n{analysis}"
                    self.telegram_client.send_message(chat_id, message)
                except ValueError:
                    logger.warning(f"Invalid chat_id format: {chat_id_str}")
            else:
                logger.warning(f"No chat_id found for session {session_id}")

            return self._success_html()
        except Exception as e:
            logger.error(f"Error handling upload: {e}")
=======
            FirestoreManager.save_message(session_id, 'assistant', f"[FILE: {filename}]\n{analysis}")

            chat_id_str = FirestoreManager.get_space_name(session_id)
            if chat_id_str:
                self.telegram_client.send_message(int(chat_id_str), f"📎 File uploaded: {filename}\n\nAnalysis:\n{analysis}")

            return self._success_html()
        except Exception as e:
            logger.error(f"UploadHandler error: {e}")
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
            return self._error_html(str(e))

    def _success_html(self) -> str:
        """Return success HTML page."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Upload Success</title>
            <style>
                body {
                    background: #1a1a1a;
                    color: #00ff00;
                    font-family: 'Courier New', monospace;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    border: 2px solid #00ff00;
                    padding: 40px;
                    border-radius: 10px;
                }
                h1 { font-size: 2em; margin-bottom: 20px; }
                p { font-size: 1.2em; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✓ Upload Successful</h1>
                <p>Your file has been analyzed.</p>
                <p>Check your chat for results.</p>
                <p style="margin-top: 30px; font-size: 0.9em;">You can close this window.</p>
            </div>
        </body>
        </html>
        """

    def _error_html(self, error: str) -> str:
        """Return error HTML page."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Upload Error</title>
            <style>
                body {{
                    background: #1a1a1a;
                    color: #ff0000;
                    font-family: 'Courier New', monospace;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                .container {{
                    text-align: center;
                    border: 2px solid #ff0000;
                    padding: 40px;
                    border-radius: 10px;
                    max-width: 600px;
                }}
                h1 {{ font-size: 2em; margin-bottom: 20px; }}
                p {{ font-size: 1.2em; }}
                .error {{ font-size: 0.9em; margin-top: 20px; color: #ff6666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✗ Upload Failed</h1>
                <p>There was an error processing your file.</p>
                <p class="error">{error}</p>
            </div>
        </body>
        </html>
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
        """Scan Drive folder for new files and process them."""
        try:
            if not GOOGLE_DRIVE_FOLDER_ID:
                return {'error': 'GOOGLE_DRIVE_FOLDER_ID not configured', 'processed': 0}

            logger.info(f"Scanning Google Drive folder: {GOOGLE_DRIVE_FOLDER_ID}")

            # List files in folder
            files = self.drive_client.list_files(
                folder_id=GOOGLE_DRIVE_FOLDER_ID,
                file_types=['.txt', '.md', '.m4a']
            )

            processed_count = 0
            results = []

            for file in files:
                file_id = file['id']
                filename = file['name']

                # Skip if already processed
                if KnowledgeBaseManager.is_processed(file_id):
                    logger.info(f"Skipping already processed file: {filename}")
                    continue

                # Process the file
                result = self.process_file(file)
                if result.get('success'):
                    processed_count += 1
                    results.append(result)

            logger.info(f"Processed {processed_count} new files")

            return {
                'success': True,
                'processed': processed_count,
                'results': results
            }
        except Exception as e:
            logger.error(f"Error scanning Drive folder: {e}")
            return {'error': str(e), 'processed': 0}

    def process_file(self, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single file from Google Drive."""
        try:
            file_id = file_metadata['id']
            filename = file_metadata['name']
            mime_type = file_metadata.get('mimeType', '')

            logger.info(f"Processing file: {filename} (ID: {file_id})")

            # Download file
            file_data = self.drive_client.download_file(file_id)
            if not file_data:
                return {'success': False, 'filename': filename, 'error': 'Download failed'}

            # Process based on file type
            # Support text files (.txt and .md), Google Docs, and PDFs
            if (mime_type in ['text/plain', 'text/markdown', 'application/octet-stream',
                             'application/vnd.google-apps.document'] or
                filename.endswith('.txt') or filename.endswith('.md')):
                try:
                    transcript = self.transcript_processor.process_text_transcript(file_data.decode('utf-8'))
                except UnicodeDecodeError:
                    # Try alternate encoding
                    transcript = self.transcript_processor.process_text_transcript(file_data.decode('latin-1'))
            elif mime_type == 'application/pdf' or filename.endswith('.pdf'):
                # Check PDF size (15 MB limit for Gemini)
                if len(file_data) > 15 * 1024 * 1024:
                    return {'success': False, 'filename': filename, 'error': 'PDF too large (max 15 MB)'}
                # Analyze PDF with Gemini multimodal
                analysis = self.gemini.analyze_multimodal(file_data, 'application/pdf', filename)
                transcript = self.transcript_processor.process_text_transcript(analysis)
            elif 'audio' in mime_type or filename.endswith('.m4a'):
                transcript = self.transcript_processor.process_audio_transcript(file_data, filename)
            else:
                return {'success': False, 'filename': filename, 'error': f'Unsupported file type: {mime_type}'}

            # Analyze transcript
            analysis = self.transcript_processor.analyze_transcript(transcript)

            # Generate interrogation questions
            questions = self.transcript_processor.generate_interrogation_questions(analysis)

            # Index in knowledge base
            KnowledgeBaseManager.index_transcript(
                file_id=file_id,
                filename=filename,
                content=transcript,
                summary=analysis,
                metadata=file_metadata
            )

            # Sync to Obsidian
            obsidian_file_id = self.obsidian_sync.sync_to_obsidian(
                filename=filename,
                content=transcript,
                summary=analysis,
                tags=['transcript', 'auto-processed'],
                metadata={**file_metadata, 'file_id': file_id}
            )

            # Create GitHub PR
            pr_url = self.github_manager.create_pr_from_transcript(
                filename=filename,
                transcript=transcript,
                analysis=analysis,
                questions=questions,
                metadata={**file_metadata, 'file_id': file_id}
            )

            # Mark as processed
            KnowledgeBaseManager.mark_as_processed(file_id)

            logger.info(f"Successfully processed {filename}: PR={pr_url}, Obsidian={obsidian_file_id}")

            return {
                'success': True,
                'filename': filename,
                'file_id': file_id,
                'pr_url': pr_url,
                'obsidian_file_id': obsidian_file_id
            }
        except Exception as e:
            logger.error(f"Error processing file {file_metadata.get('name')}: {e}")
            return {'success': False, 'filename': file_metadata.get('name'), 'error': str(e)}


<<<<<<< HEAD
=======
# --------------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------------
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def jsonify_with_cors(data, status=200):
    return add_cors_headers(make_response(jsonify(data), status))

>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
def get_upload_ui_html(session_id: str) -> str:
    """Generate the upload UI HTML."""
    upload_url = f"{FUNCTION_URL}?mode=upload&session={session_id}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>V2V2B Interrogator - Upload</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                color: #00ff41;
                font-family: 'Courier New', monospace;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .container {{
                background: rgba(26, 26, 46, 0.9);
                border: 2px solid #00ff41;
                border-radius: 15px;
                padding: 40px;
                max-width: 500px;
                width: 100%;
                box-shadow: 0 0 30px rgba(0, 255, 65, 0.3);
            }}
            h1 {{
                font-size: 1.8em;
                margin-bottom: 10px;
                text-align: center;
                text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
            }}
            .session-id {{
                text-align: center;
                font-size: 0.8em;
                color: #888;
                margin-bottom: 30px;
                word-break: break-all;
            }}
            .upload-area {{
                border: 2px dashed #00ff41;
                border-radius: 10px;
                padding: 40px 20px;
                text-align: center;
                margin-bottom: 20px;
                transition: all 0.3s;
                cursor: pointer;
            }}
            .upload-area:hover {{
                background: rgba(0, 255, 65, 0.1);
                border-color: #00ff88;
            }}
            .upload-area.dragover {{
                background: rgba(0, 255, 65, 0.2);
                border-color: #00ff88;
            }}
            input[type="file"] {{
                display: none;
            }}
            .file-icon {{
                font-size: 3em;
                margin-bottom: 10px;
            }}
            .upload-text {{
                font-size: 1.1em;
                margin-bottom: 10px;
            }}
            .file-types {{
                font-size: 0.9em;
                color: #888;
            }}
            .selected-file {{
                background: rgba(0, 255, 65, 0.1);
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                display: none;
            }}
            .selected-file.show {{
                display: block;
            }}
            button {{
                width: 100%;
                padding: 15px;
                background: #00ff41;
                color: #0a0a0a;
                border: none;
                border-radius: 5px;
                font-size: 1.1em;
                font-weight: bold;
                font-family: 'Courier New', monospace;
                cursor: pointer;
                transition: all 0.3s;
                text-transform: uppercase;
            }}
            button:hover {{
                background: #00ff88;
                box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
            }}
            button:disabled {{
                background: #555;
                cursor: not-allowed;
                box-shadow: none;
            }}
            .loading {{
                display: none;
                text-align: center;
                margin-top: 20px;
            }}
            .loading.show {{
                display: block;
            }}
            .spinner {{
                border: 3px solid rgba(0, 255, 65, 0.3);
                border-top: 3px solid #00ff41;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📎 V2V2B Interrogator</h1>
            <div class="session-id">Session: {session_id}</div>

            <form id="uploadForm" enctype="multipart/form-data">
                <div class="upload-area" id="uploadArea">
                    <div class="file-icon">📁</div>
                    <div class="upload-text">Click to select or drag & drop</div>
                    <div class="file-types">Audio, Image, Text, or PDF files</div>
                    <input type="file" id="fileInput" name="file" accept="audio/*,image/*,text/plain,.txt,.md,.pdf,application/pdf" required>
                </div>

                <div class="selected-file" id="selectedFile">
                    <strong>Selected:</strong> <span id="fileName"></span>
                </div>

                <button type="submit" id="uploadBtn">Upload & Analyze</button>
            </form>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <div>Processing your file...</div>
            </div>
        </div>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const uploadForm = document.getElementById('uploadForm');
            const uploadBtn = document.getElementById('uploadBtn');
            const selectedFile = document.getElementById('selectedFile');
            const fileName = document.getElementById('fileName');
            const loading = document.getElementById('loading');

            // Click to select file
            uploadArea.addEventListener('click', () => fileInput.click());

            // File selected
            fileInput.addEventListener('change', (e) => {{
                if (e.target.files.length > 0) {{
                    fileName.textContent = e.target.files[0].name;
                    selectedFile.classList.add('show');
                }}
            }});

            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {{
                e.preventDefault();
                uploadArea.classList.add('dragover');
            }});

            uploadArea.addEventListener('dragleave', () => {{
                uploadArea.classList.remove('dragover');
            }});

            uploadArea.addEventListener('drop', (e) => {{
                e.preventDefault();
                uploadArea.classList.remove('dragover');

                if (e.dataTransfer.files.length > 0) {{
                    fileInput.files = e.dataTransfer.files;
                    fileName.textContent = e.dataTransfer.files[0].name;
                    selectedFile.classList.add('show');
                }}
            }});

            // Form submission
            uploadForm.addEventListener('submit', async (e) => {{
                e.preventDefault();

                if (fileInput.files.length === 0) {{
                    alert('Please select a file first');
                    return;
                }}

                uploadBtn.disabled = true;
                loading.classList.add('show');

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                try {{
                    const response = await fetch('{upload_url}', {{
                        method: 'POST',
                        body: formData
                    }});

                    const html = await response.text();
                    document.body.innerHTML = html;
                }} catch (error) {{
                    alert('Upload failed: ' + error.message);
                    uploadBtn.disabled = false;
                    loading.classList.remove('show');
                }}
            }});
        </script>
    </body>
    </html>
    """

<<<<<<< HEAD

def add_cors_headers(response):
    """Add CORS headers to response for browser compatibility."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response


def jsonify_with_cors(data, status_code=200):
    """Create JSON response with CORS headers to ensure all responses include CORS."""
    response = make_response(jsonify(data), status_code)
    return add_cors_headers(response)


# Module initialization complete
logger.info("=" * 80)
logger.info("MODULE INITIALIZATION COMPLETE")
logger.info("Entry point ready to receive requests")
logger.info("=" * 80)


=======
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
@functions_framework.http
def entry_point(request):
    """
    Main entry point for the Cloud Function.
    Routes requests based on method and query parameters.
    """
<<<<<<< HEAD
    # Extract request ID for tracing
    request_id = request.headers.get('X-Cloud-Trace-Context', 'no-trace')[:16]

    # Log incoming request details
    logger.info(f"[{request_id}] === NEW REQUEST ===")
    logger.info(f"[{request_id}] Method: {request.method}")
    logger.info(f"[{request_id}] Path: {request.path}")
    logger.info(f"[{request_id}] Query Args: {dict(request.args)}")
    logger.info(f"[{request_id}] Origin: {request.headers.get('Origin', 'N/A')}")

    try:
        # Handle CORS preflight requests
        if request.method == 'OPTIONS':
            logger.info(f"[{request_id}] CORS preflight request")
            response = make_response('', 204)
            return add_cors_headers(response)
        # Get query parameters and path
        mode = request.args.get('mode', '')
        session_id = request.args.get('session', '')
        path = request.path

        logger.info(f"[{request_id}] Route: mode={mode}, path={path}, session={session_id}")

        # Route A: Telegram Webhook (POST /telegram)
        if request.method == 'POST' and path == '/telegram':
            # Parse Telegram Update
            update_data = request.get_json(silent=True)
            if not update_data:
                return jsonify_with_cors({'error': 'Invalid request body'}, 400)

            handler = TelegramWebhookHandler()
            response = handler.handle(update_data)
            return jsonify_with_cors(response)

        # Route B: Upload UI (GET /?mode=ui&session=...)
        elif request.method == 'GET' and mode == 'ui':
            if not session_id:
                response = make_response('Missing session parameter', 400)
                return add_cors_headers(response)

            html = get_upload_ui_html(session_id)
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html'
            return add_cors_headers(response)

        # Route C: File Upload Handler (POST /?mode=upload&session=...)
        elif request.method == 'POST' and mode == 'upload':
            if not session_id:
                response = make_response('Missing session parameter', 400)
                return add_cors_headers(response)

            # Get uploaded file
            if 'file' not in request.files:
                response = make_response('No file uploaded', 400)
                return add_cors_headers(response)

            file = request.files['file']
            if file.filename == '':
                response = make_response('Empty filename', 400)
                return add_cors_headers(response)

            # Read file data
            file_data = file.read()
            filename = file.filename
            content_type = file.content_type or 'application/octet-stream'

            # Process upload
            handler = UploadHandler()
            html_response = handler.handle(session_id, file_data, filename, content_type)

            response = make_response(html_response)
            response.headers['Content-Type'] = 'text/html'
            return add_cors_headers(response)

        # Route D: Manual Drive Scan (GET /?mode=scan)
        elif request.method == 'GET' and mode == 'scan':
            handler = DriveMonitorHandler()
            result = handler.scan_and_process_new_files()
            return jsonify_with_cors(result, 200)

        # Route E: Drive Webhook Handler (POST /?mode=drive_webhook)
        elif request.method == 'POST' and mode == 'drive_webhook':
            # Google Drive push notification webhook
            # This will be called when new files are added to the watched folder
            handler = DriveMonitorHandler()
            result = handler.scan_and_process_new_files()
            return jsonify_with_cors(result, 200)

        # Route F: Repository Health Check (GET /health/repos or GET /?mode=health_repos)
        elif request.method == 'GET' and (path == '/health/repos' or mode == 'health_repos'):
            logger.info(f"[{request_id}] Repository health check requested")
            try:
                config_manager = GitHubConfigManager.get_instance()

                results = {
                    'status': 'healthy',
                    'config_version': config_manager.config_data.get('version'),
                    'default_repository': config_manager.default_repo_label,
                    'repositories': []
                }

                for label, repo_config in config_manager.repositories.items():
                    repo_status = {
                        'label': label,
                        'name': repo_config.name,
                        'token_env_var': repo_config.token_env_var,
                        'token_available': bool(os.environ.get(repo_config.token_env_var)),
                        'accessible': False,
                        'error': None
                    }

                    # Test repository access
                    try:
                        repo = repo_config.get_repo()
                        _ = repo.default_branch  # Simple read operation
                        repo_status['accessible'] = True
                    except Exception as e:
                        repo_status['error'] = str(e)
                        results['status'] = 'degraded'
                        logger.error(f"Repository {label} not accessible: {e}")

                    results['repositories'].append(repo_status)

                # Determine HTTP status code
                if results['status'] == 'healthy':
                    status_code = 200
                elif results['status'] == 'degraded':
                    status_code = 503  # Service Unavailable (partial functionality)
                else:
                    status_code = 500

                return jsonify_with_cors(results, status_code)

            except Exception as e:
                logger.error(f"Health check failed: {e}", exc_info=True)
                return jsonify_with_cors({
                    'status': 'unhealthy',
                    'error': str(e)
                }, 503)

        # Route G: Health Check (GET /)
        elif request.method == 'GET' and not mode:
            logger.info(f"[{request_id}] Health check requested")

            health_status = {
                'status': 'healthy',
                'service': 'V2V2B Interrogator',
                'version': '2.0.0',
                'timestamp': datetime.utcnow().isoformat(),
            }

            # Check environment variables
            env_check = {
                'GCP_PROJECT': bool(GCP_PROJECT),
                'TELEGRAM_BOT_TOKEN': bool(TELEGRAM_BOT_TOKEN),
                'GITHUB_TOKEN': bool(GITHUB_TOKEN),
                'REPO_NAME': bool(REPO_NAME),
                'FUNCTION_URL': bool(FUNCTION_URL)
            }
            health_status['environment'] = env_check

            # Check if all required vars are set
            all_env_ok = all(env_check.values())
            if not all_env_ok:
                health_status['status'] = 'degraded'
                health_status['warning'] = 'Some environment variables not set'
                logger.warning(f"[{request_id}] Health check: degraded - missing environment variables")

            # Test lazy initialization of dependencies
            try:
                db = get_db()
                health_status['firestore'] = 'connected'
                logger.info(f"[{request_id}] Health check: Firestore OK")
            except Exception as e:
                health_status['firestore'] = f'error: {str(e)}'
                health_status['status'] = 'unhealthy'
                logger.error(f"[{request_id}] Health check: Firestore FAILED - {e}")

            try:
                ensure_vertexai_initialized()
                health_status['vertexai'] = 'initialized'
                logger.info(f"[{request_id}] Health check: Vertex AI OK")
            except Exception as e:
                health_status['vertexai'] = f'error: {str(e)}'
                health_status['status'] = 'unhealthy'
                logger.error(f"[{request_id}] Health check: Vertex AI FAILED - {e}")

            health_status['endpoints'] = {
                'telegram_webhook': 'POST /telegram',
                'upload_ui': 'GET /?mode=ui&session=SESSION_ID',
                'file_upload': 'POST /?mode=upload&session=SESSION_ID',
                'drive_scan': 'GET /?mode=scan',
                'drive_webhook': 'POST /?mode=drive_webhook'
            }

            health_status['features'] = [
                'Telegram bot',
                'Multimodal file analysis',
                'Google Drive monitoring',
                'Transcript processing (.txt, .m4a)',
                'Knowledge base indexing',
                'Obsidian vault sync',
                'Automated PR creation'
            ]

            status_code = 200 if health_status['status'] == 'healthy' else 503
            logger.info(f"[{request_id}] Health check result: {health_status['status']}")

            return jsonify_with_cors(health_status, status_code)

        else:
            return jsonify_with_cors({'error': 'Invalid request'}, 400)

    except Exception as e:
        logger.error(f"[{request_id}] Unhandled error in entry_point: {e}", exc_info=True)
        logger.error(f"[{request_id}] Error type: {type(e).__name__}")
        logger.error(f"[{request_id}] Error args: {e.args}")

        # Return detailed error for debugging
        error_detail = {
            'error': str(e),
            'error_type': type(e).__name__,
            'request_id': request_id
        }

        # Include traceback in development mode
        if os.environ.get('ENV') == 'development':
            import traceback
            error_detail['traceback'] = traceback.format_exc()

        return jsonify_with_cors(error_detail, 500)
=======
    if request.method == 'OPTIONS':
        return add_cors_headers(make_response('', 204))

    path = request.path
    mode = request.args.get('mode', '')
    session_id = request.args.get('session', '')

    try:
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

        elif request.method == 'GET' and mode == 'ui':
            return add_cors_headers(make_response(get_upload_ui_html(session_id)))

        elif request.method == 'POST' and mode == 'upload':
            file = request.files['file']
            handler = UploadHandler()
            html = handler.handle(session_id, file.read(), file.filename, file.content_type)
            return add_cors_headers(make_response(html))

        elif mode == 'scan' or mode == 'drive_webhook':
             handler = DriveMonitorHandler()
             result = handler.scan_and_process_new_files()
             return jsonify_with_cors(result)

        return jsonify_with_cors({'status': 'healthy', 'service': 'V2V2B Interrogator v2.0'})

    except Exception as e:
        logger.error(f"Entry point error: {e}", exc_info=True)
        return jsonify_with_cors({'error': str(e)}, 500)
>>>>>>> fab5f408803fee420f6fa1806b5d92e1deb5eca7
