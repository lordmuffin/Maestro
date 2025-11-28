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
import io
import asyncio

from flask import Flask, request, jsonify, make_response
import functions_framework
from google.cloud import firestore
from google.cloud import aiplatform
from google.cloud import logging as cloud_logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from github import Github
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth import default
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
TARGET_FUNCTION_NAME = "YOUR_FUNCTION_NAME"  # Placeholder

# Safe integer conversion with error handling
try:
    DRIVE_POLL_INTERVAL = int(os.environ.get('DRIVE_POLL_INTERVAL', '300'))
    logger.info(f"DRIVE_POLL_INTERVAL set to {DRIVE_POLL_INTERVAL} seconds")
except ValueError as e:
    logger.warning(f"Invalid DRIVE_POLL_INTERVAL value, using default 300: {e}")
    DRIVE_POLL_INTERVAL = 300

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
        return get_db().collection('sessions').document(session_id)

    @staticmethod
    def save_message(session_id: str, role: str, content: str, space_name: str = None):
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
            if file_data:
                validation_data['file_data_base64'] = base64.b64encode(file_data).decode('utf-8')
            validation_ref.set(validation_data)
            logger.info(f"Saved pending validation {validation_id}")
        except Exception as e:
            logger.error(f"Error saving pending validation: {e}")
            raise

    @staticmethod
    def get_pending_validation(validation_id: str) -> Optional[Dict[str, Any]]:
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
    """Handles Google Drive operations."""

    def __init__(self):
        self._service = None
        self._initialized = False

    def _ensure_initialized(self):
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
        self._ensure_initialized()
        return self._service

    def list_files(self, folder_id: str, file_types: List[str] = None) -> List[Dict[str, Any]]:
        try:
            if not folder_id:
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
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return []

    def download_file(self, file_id: str) -> Optional[bytes]:
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
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}", exc_info=True)
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size"
            ).execute()
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None

    def upload_file(self, folder_id: str, filename: str, content: str, mime_type: str = 'text/markdown') -> Optional[str]:
        try:
            from googleapiclient.http import MediaInMemoryUpload
            file_metadata = {'name': filename, 'parents': [folder_id]}
            media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            return None

    def update_file_content(self, file_id: str, new_content: str) -> bool:
        try:
            from googleapiclient.http import MediaInMemoryUpload
            metadata = self.get_file_metadata(file_id)
            mime_type = metadata.get('mimeType', 'text/plain') if metadata else 'text/plain'
            media = MediaInMemoryUpload(new_content.encode('utf-8'), mimetype=mime_type)
            self.service.files().update(fileId=file_id, media_body=media).execute()
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
        try:
            if self._kanban_file_id: return self._kanban_file_id
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_client.service.files().list(q=query, fields='files(id, name, modifiedTime)', orderBy='modifiedTime desc').execute()
            files = results.get('files', [])
            if not files: return None
            self._kanban_file_id = files[0]['id']
            return self._kanban_file_id
        except Exception as e:
            logger.error(f"Error finding Kanban file: {e}", exc_info=True)
            return None

    def extract_action_items(self, note_content: str, note_title: str) -> List[Dict[str, str]]:
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
        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            return []

    def transform_to_kanban_format(self, action_items: List[Dict[str, str]], source_note_title: str) -> List[str]:
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
            return False


class KnowledgeBaseManager:
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
        except Exception as e:
            logger.error(f"Error indexing transcript: {e}")
            raise

    @staticmethod
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
        except Exception as e:
            logger.error(f"Error syncing to Obsidian: {e}")
            return None


class TranscriptProcessor:
    """Processes transcript files."""
    def __init__(self, gemini_client):
        self.gemini = gemini_client

    def process_text_transcript(self, text_content: str) -> str:
        return text_content

    def process_audio_transcript(self, audio_data: bytes, filename: str) -> str:
        try:
            part = Part.from_data(data=audio_data, mime_type='audio/mp4')
            prompt_part = Part.from_text("Transcribe this audio recording.")
            response = self.gemini.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return f"[Transcription failed: {str(e)}]"

    def analyze_transcript(self, transcript_text: str) -> str:
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
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return f"Question generation failed: {str(e)}"


class GeminiClient:
    """Handles interactions with Vertex AI Gemini models."""
    def __init__(self):
        ensure_vertexai_initialized()
        self.model = GenerativeModel("gemini-2.5-flash")

    def chat_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
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
            return f"Error analyzing file: {str(e)}"


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
            logger.error(f"Failed to load repository configuration: {e}")
            raise

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

            if content_type in ['application/pdf', 'audio/*', 'image/*', 'video/*'] or content_type.startswith(('audio/', 'image/', 'video/')):
                analysis = self.gemini.analyze_multimodal(file_data, content_type, filename)
            elif content_type == 'text/plain' or filename.endswith(('.txt', '.md')):
                analysis = file_data.decode('utf-8')
            else:
                return self._error_html(f'Unsupported file type: {content_type}')

            FirestoreManager.save_message(session_id, 'assistant', f"[FILE: {filename}]\n{analysis}")

            chat_id_str = FirestoreManager.get_space_name(session_id)
            if chat_id_str:
                self.telegram_client.send_message(int(chat_id_str), f"📎 File uploaded: {filename}\n\nAnalysis:\n{analysis}")

            return self._success_html()
        except Exception as e:
            logger.error(f"UploadHandler error: {e}")
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
