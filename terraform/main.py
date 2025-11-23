"""
V2V2B Interrogator - Telegram Bot for Technical Content Extraction
A serverless application that interrogates technical authors via Telegram
and processes multimodal inputs (text, audio, images) using Gemini AI.
"""

import os
import sys
import logging
import json
from datetime import datetime
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
from telegram.error import TelegramError
import asyncio
import io

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
if not GITHUB_TOKEN:
    missing_vars.append('GITHUB_TOKEN')
if not REPO_NAME:
    missing_vars.append('REPO_NAME')

if missing_vars:
    logger.error(f"CRITICAL: Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Function may fail when these are accessed")
else:
    logger.info("All critical environment variables are set")

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

Format as a markdown checklist suitable for a GitHub PR."""
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
            request = self.service.files().get_media(fileId=file_id)
            file_data = request.execute()
            logger.info(f"Downloaded file {file_id}, size: {len(file_data)} bytes")
            return file_data
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
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
        """Analyze audio or image file."""
        try:
            # Create the appropriate Part based on file type
            if mime_type.startswith('image/'):
                part = Part.from_data(data=file_data, mime_type=mime_type)
            elif mime_type.startswith('audio/'):
                part = Part.from_data(data=file_data, mime_type=mime_type)
            else:
                return f"Unsupported file type: {mime_type}"

            # Create prompt
            prompt_part = Part.from_text(f"{get_prompt('multimodal_analysis_prompt.md')}\n\nFile: {filename}")

            # Generate analysis
            response = self.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
            return f"Error analyzing file: {str(e)}"


class GitHubManager:
    """Handles GitHub operations for PR creation."""

    def __init__(self):
        self._github = None
        self._repo = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of GitHub client to prevent cold start issues."""
        if self._initialized:
            return

        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN not configured")
        if not REPO_NAME:
            raise ValueError("REPO_NAME not configured")

        try:
            self._github = Github(GITHUB_TOKEN)
            self._repo = self._github.get_repo(REPO_NAME)
            self._initialized = True
            logger.info(f"Initialized GitHub client for repo: {REPO_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            raise

    @property
    def repo(self):
        """Lazy-loaded repository reference."""
        self._ensure_initialized()
        return self._repo

    @property
    def github(self):
        """Lazy-loaded GitHub client."""
        self._ensure_initialized()
        return self._github

    def create_pr_from_session(self, session_id: str, history: List[Dict[str, str]]) -> str:
        """Create a branch, commit session content, and open PR."""
        try:
            # Generate branch name
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            branch_name = f"session/{session_id.replace('@', '-').replace('.', '-')}-{timestamp}"

            # Get default branch
            default_branch = self.repo.default_branch
            source = self.repo.get_branch(default_branch)

            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Created branch: {branch_name}")

            # Format history as markdown
            markdown_content = self._format_history_as_markdown(session_id, history)

            # Create filename
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            filename = f"sessions/{date_str}-{session_id.split('@')[0]}.md"

            # Commit file
            self.repo.create_file(
                path=filename,
                message=f"Add session content: {session_id}",
                content=markdown_content,
                branch=branch_name
            )
            logger.info(f"Committed file: {filename}")

            # Create PR
            pr = self.repo.create_pull(
                title=f"Session Content: {session_id}",
                body=f"Automated PR containing content from interrogation session `{session_id}`.\n\nGenerated by V2V2B Interrogator.",
                head=branch_name,
                base=default_branch
            )
            logger.info(f"Created PR: {pr.html_url}")

            return pr.html_url
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            raise

    def create_pr_from_transcript(self, filename: str, transcript: str, analysis: str, questions: str, metadata: Dict[str, Any]) -> str:
        """Create a PR with transcript analysis and interrogation questions."""
        try:
            # Generate branch name from filename and timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            safe_filename = filename.replace('.', '-').replace(' ', '-')
            branch_name = f"transcript/{safe_filename}-{timestamp}"

            # Get default branch
            default_branch = self.repo.default_branch
            source = self.repo.get_branch(default_branch)

            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            logger.info(f"Created branch: {branch_name}")

            # Format as markdown
            markdown_content = self._format_transcript_as_markdown(filename, transcript, analysis, questions, metadata)

            # Create filename for transcripts directory
            date_str = datetime.now().strftime('%Y-%m-%d')
            base_name = filename.rsplit('.', 1)[0]
            file_path = f"transcripts/{date_str}-{base_name}.md"

            # Commit file
            self.repo.create_file(
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

            pr = self.repo.create_pull(
                title=f"📋 Transcript Analysis: {filename}",
                body=pr_body,
                head=branch_name,
                base=default_branch
            )
            logger.info(f"Created PR: {pr.html_url}")

            return pr.html_url
        except Exception as e:
            logger.error(f"Error creating transcript PR: {e}")
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

    def send_message(self, chat_id: int, text: str, reply_markup=None) -> bool:
        """Send a message to a Telegram chat."""
        try:
            # Run async send_message in sync context
            asyncio.run(self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            ))
            logger.info(f"Message sent to chat_id {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to Telegram: {e}")
            return False

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file from Telegram using file_id."""
        try:
            async def _download():
                file = await self.bot.get_file(file_id)
                file_bytes = await file.download_as_bytearray()
                return bytes(file_bytes)

            result = asyncio.run(_download())
            logger.info(f"Downloaded file {file_id}")
            return result
        except TelegramError as e:
            logger.error(f"Error downloading file from Telegram: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            return None

    def answer_callback_query(self, callback_query_id: str, text: str = None) -> bool:
        """Answer a callback query from inline keyboard."""
        try:
            asyncio.run(self.bot.answer_callback_query(callback_query_id=callback_query_id, text=text))
            logger.info(f"Answered callback query {callback_query_id}")
            return True
        except TelegramError as e:
            logger.error(f"Error answering callback query: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error answering callback query: {e}")
            return False


class TelegramWebhookHandler:
    """Handles Telegram webhook events."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.github_manager = GitHubManager()
        self.telegram_client = TelegramClient()

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
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
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
        welcome_text += "/help - Show help information\n\n"
        welcome_text += "Just send me a message to start our technical interview!"

        self.telegram_client.send_message(chat_id, welcome_text)
        return {'status': 'ok'}

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
        """Handle /done command - complete session."""
        try:
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
            self.telegram_client.send_message(chat_id, f'❌ Error creating PR: {str(e)}')
            return {'status': 'error'}

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

                # Support .txt and .md files
                if (mime_type == 'text/plain' or mime_type == 'text/markdown' or
                    filename.endswith('.txt') or filename.endswith('.md')):
                    return self._process_text_file(session_id, chat_id, document)
                else:
                    self.telegram_client.send_message(chat_id, '❌ Only .txt and .md files are supported for documents.')
                    return {'status': 'error'}
            elif 'audio' in message or 'photo' in message:
                # Redirect audio and photos to web UI (can be extended later)
                info_text = "📎 For audio and images, please use the web interface:\n"
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

            self.telegram_client.send_message(chat_id, f'📄 Processing text file: *{filename}*...')

            # Download file
            file_data = self.telegram_client.download_file(file_id)
            if not file_data:
                self.telegram_client.send_message(chat_id, '❌ Failed to download file.')
                return {'status': 'error'}

            # Decode text content
            try:
                content = file_data.decode('utf-8')
            except UnicodeDecodeError:
                content = file_data.decode('latin-1')  # Fallback encoding

            # Generate structured notes using validation prompt
            structured_notes = self._generate_structured_notes(content, filename, 'text')

            # Create validation ID
            validation_id = f"{session_id}_{file_id}"

            # Save to pending validations
            FirestoreManager.save_pending_validation(
                validation_id=validation_id,
                session_id=session_id,
                chat_id=chat_id,
                file_type='text',
                filename=filename,
                content=content,
                structured_notes=structured_notes
            )

            # Send preview with validation buttons
            self._send_validation_prompt(chat_id, filename, structured_notes, validation_id)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing text file: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing text file: {str(e)}')
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
            filename = f"voice_recording_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.ogg"

            self.telegram_client.send_message(chat_id, f'🎤 Processing voice recording ({duration}s)...')

            # Download voice file
            file_data = self.telegram_client.download_file(file_id)
            if not file_data:
                self.telegram_client.send_message(chat_id, '❌ Failed to download voice recording.')
                return {'status': 'error'}

            # Transcribe and analyze with Gemini (audio/ogg format)
            analysis = self.gemini.analyze_multimodal(file_data, 'audio/ogg', filename)

            # Generate structured notes
            structured_notes = self._generate_structured_notes(analysis, filename, 'voice')

            # Create validation ID
            validation_id = f"{session_id}_{file_id}"

            # Save to pending validations
            FirestoreManager.save_pending_validation(
                validation_id=validation_id,
                session_id=session_id,
                chat_id=chat_id,
                file_type='voice',
                filename=filename,
                content=analysis,
                structured_notes=structured_notes,
                file_data=file_data
            )

            # Send preview with validation buttons
            self._send_validation_prompt(chat_id, filename, structured_notes, validation_id)

            return {'status': 'ok'}

        except Exception as e:
            logger.error(f"Error processing voice recording: {e}", exc_info=True)
            self.telegram_client.send_message(chat_id, f'❌ Error processing voice: {str(e)}')
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
            max_length = 3500
            preview = structured_notes[:max_length]
            if len(structured_notes) > max_length:
                preview += "\n\n... (truncated for preview)"

            message_text = f"📋 *Preview of structured notes for:* `{filename}`\n\n"
            message_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            message_text += preview
            message_text += "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            message_text += "\n*Please validate this content:*"

            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Validate & Save", callback_data=f"validate:{validation_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject:{validation_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            self.telegram_client.send_message(chat_id, message_text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error sending validation prompt: {e}")
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

    def _handle_chat_message(self, session_id: str, chat_id: int, username: str, message_text: str) -> Dict[str, Any]:
        """Handle regular chat message."""
        try:
            # Save user message (use chat_id as space_name)
            FirestoreManager.save_message(session_id, 'user', message_text, str(chat_id))

            # Get history
            history = FirestoreManager.get_session_history(session_id)

            # Generate response
            bot_response = self.gemini.chat_response(message_text, history)

            # Save bot response
            FirestoreManager.save_message(session_id, 'assistant', bot_response, str(chat_id))

            # Send response via Telegram
            self.telegram_client.send_message(chat_id, bot_response)

            return {'status': 'ok'}
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            self.telegram_client.send_message(chat_id, '❌ Sorry, I encountered an error processing your message.')
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

            # Analyze file with Gemini
            analysis = self.gemini.analyze_multimodal(file_data, content_type, filename)

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
            # Support text files (.txt and .md)
            if (mime_type in ['text/plain', 'text/markdown', 'application/octet-stream'] or
                filename.endswith('.txt') or filename.endswith('.md')):
                try:
                    transcript = self.transcript_processor.process_text_transcript(file_data.decode('utf-8'))
                except UnicodeDecodeError:
                    # Try alternate encoding
                    transcript = self.transcript_processor.process_text_transcript(file_data.decode('latin-1'))
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
                    <div class="file-types">Audio, Image, or Text files</div>
                    <input type="file" id="fileInput" name="file" accept="audio/*,image/*,text/plain,.txt,.md" required>
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


@functions_framework.http
def entry_point(request):
    """
    Main entry point for the Cloud Function.
    Routes requests based on method and query parameters.
    """
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

        # Route F: Health Check (GET /)
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
