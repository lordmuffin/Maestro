"""
V2V2B Interrogator - Google Chat Bot for Technical Content Extraction
A serverless application that interrogates technical authors via Google Chat
and processes multimodal inputs (text, audio, images) using Gemini AI.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
GCP_PROJECT = os.environ.get('GCP_PROJECT')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_NAME = os.environ.get('REPO_NAME')
FUNCTION_URL = os.environ.get('FUNCTION_URL')

# Initialize Firestore
db = firestore.Client(project=GCP_PROJECT)

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT, location="us-central1")

# System prompts
CHAT_SYSTEM_PROMPT = """You are a sarcastic but insightful Enterprise Architect conducting a technical interview.
Your goal is to extract detailed architectural knowledge from the user through probing questions.
Be direct, occasionally sarcastic, but always professional. Ask follow-up questions that dig deeper.
Focus on: design decisions, trade-offs, scalability, security, and real-world implementation challenges."""

MULTIMODAL_SYSTEM_PROMPT = """Analyze this raw input (audio or image) and extract all architectural concepts,
technical details, design patterns, and implementation insights. Be thorough and structured in your analysis."""


class FirestoreManager:
    """Manages Firestore operations for session history."""

    @staticmethod
    def get_session_ref(session_id: str):
        """Get Firestore document reference for a session."""
        return db.collection('sessions').document(session_id)

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


class GeminiClient:
    """Handles interactions with Vertex AI Gemini models."""

    def __init__(self):
        self.model = GenerativeModel("gemini-1.5-flash-002")

    def chat_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
        """Generate a chat response with context."""
        try:
            # Build conversation history
            contents = []

            # Add system instruction as first user message with context
            contents.append(Content(
                role="user",
                parts=[Part.from_text(CHAT_SYSTEM_PROMPT)]
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
            prompt_part = Part.from_text(f"{MULTIMODAL_SYSTEM_PROMPT}\n\nFile: {filename}")

            # Generate analysis
            response = self.model.generate_content([prompt_part, part])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing multimodal content: {e}")
            return f"Error analyzing file: {str(e)}"


class GitHubManager:
    """Handles GitHub operations for PR creation."""

    def __init__(self):
        self.github = Github(GITHUB_TOKEN)
        self.repo = self.github.get_repo(REPO_NAME)

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

    def _format_history_as_markdown(self, session_id: str, history: List[Dict[str, str]]) -> str:
        """Format session history as markdown."""
        lines = [
            f"# Session: {session_id}",
            f"\n**Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
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


class GoogleChatClient:
    """Handles Google Chat API operations."""

    def __init__(self):
        # Get default credentials
        credentials, _ = default()
        self.service = build('chat', 'v1', credentials=credentials)

    def send_message(self, space_name: str, text: str) -> bool:
        """Send a message to a Google Chat space."""
        try:
            message = {
                'text': text
            }

            result = self.service.spaces().messages().create(
                parent=space_name,
                body=message
            ).execute()

            logger.info(f"Message sent to {space_name}: {result.get('name')}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to Google Chat: {e}")
            return False


class ChatWebhookHandler:
    """Handles Google Chat webhook events."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.github_manager = GitHubManager()

    def handle(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming chat webhook."""
        try:
            # Extract event type
            event_type = event_data.get('type')

            # Handle different event types
            if event_type == 'ADDED_TO_SPACE':
                return {'text': '👋 Hello! I\'m the V2V2B Interrogator. Ready to extract some architectural wisdom?'}

            if event_type == 'REMOVED_FROM_SPACE':
                return {}

            # Handle MESSAGE event
            message = event_data.get('message', {})
            space = event_data.get('space', {})
            user = event_data.get('user', {})

            # Extract data
            user_email = user.get('email', 'unknown@example.com')
            space_name = space.get('name', '')
            message_text = message.get('text', '').strip()

            # Generate session ID
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            session_id = f"{user_email}_{date_str}"

            logger.info(f"Processing message from {user_email} in {space_name}: {message_text}")

            # Route based on message content
            if 'UPLOAD' in message_text.upper() or 'LINK' in message_text.upper():
                return self._handle_upload_request(session_id, space_name)

            elif message_text.upper() == 'DONE':
                return self._handle_done_request(session_id)

            else:
                return self._handle_chat_message(session_id, space_name, user_email, message_text)

        except Exception as e:
            logger.error(f"Error handling chat webhook: {e}")
            return {'text': f'Error processing your request: {str(e)}'}

    def _handle_upload_request(self, session_id: str, space_name: str) -> Dict[str, Any]:
        """Handle upload/link request."""
        # Ensure space name is saved
        FirestoreManager.save_message(session_id, 'system', 'Upload requested', space_name)

        upload_url = f"{FUNCTION_URL}?mode=ui&session={session_id}"
        return {
            'text': f'📎 Ready to upload? Click here:\n{upload_url}\n\n(Upload audio or images for analysis)'
        }

    def _handle_done_request(self, session_id: str) -> Dict[str, Any]:
        """Handle session completion request."""
        try:
            history = FirestoreManager.get_session_history(session_id)

            if not history:
                return {'text': 'No session history found. Start chatting first!'}

            # Create PR
            pr_url = self.github_manager.create_pr_from_session(session_id, history)

            return {
                'text': f'✅ Session complete! Pull request created:\n{pr_url}'
            }
        except Exception as e:
            logger.error(f"Error handling DONE request: {e}")
            return {'text': f'Error creating PR: {str(e)}'}

    def _handle_chat_message(self, session_id: str, space_name: str, user_email: str, message_text: str) -> Dict[str, Any]:
        """Handle regular chat message."""
        try:
            # Save user message
            FirestoreManager.save_message(session_id, 'user', message_text, space_name)

            # Get history
            history = FirestoreManager.get_session_history(session_id)

            # Generate response
            bot_response = self.gemini.chat_response(message_text, history)

            # Save bot response
            FirestoreManager.save_message(session_id, 'assistant', bot_response, space_name)

            return {'text': bot_response}
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            return {'text': 'Sorry, I encountered an error processing your message.'}


class UploadHandler:
    """Handles file upload processing."""

    def __init__(self):
        self.gemini = GeminiClient()
        self.chat_client = GoogleChatClient()

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

            # Get space name and send message back to chat
            space_name = FirestoreManager.get_space_name(session_id)
            if space_name:
                message = f"📎 File analyzed: *{filename}*\n\n{analysis}"
                self.chat_client.send_message(space_name, message)
            else:
                logger.warning(f"No space name found for session {session_id}")

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
                    <div class="file-types">Audio or Image files</div>
                    <input type="file" id="fileInput" name="file" accept="audio/*,image/*" required>
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
    try:
        # Get query parameters
        mode = request.args.get('mode', '')
        session_id = request.args.get('session', '')

        # Route A: Chat Webhook (POST /)
        if request.method == 'POST' and not mode:
            # Parse Google Chat event
            event_data = request.get_json(silent=True)
            if not event_data:
                return jsonify({'error': 'Invalid request body'}), 400

            handler = ChatWebhookHandler()
            response = handler.handle(event_data)
            return jsonify(response)

        # Route B: Upload UI (GET /?mode=ui&session=...)
        elif request.method == 'GET' and mode == 'ui':
            if not session_id:
                return 'Missing session parameter', 400

            html = get_upload_ui_html(session_id)
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html'
            return response

        # Route C: File Upload Handler (POST /?mode=upload&session=...)
        elif request.method == 'POST' and mode == 'upload':
            if not session_id:
                return 'Missing session parameter', 400

            # Get uploaded file
            if 'file' not in request.files:
                return 'No file uploaded', 400

            file = request.files['file']
            if file.filename == '':
                return 'Empty filename', 400

            # Read file data
            file_data = file.read()
            filename = file.filename
            content_type = file.content_type or 'application/octet-stream'

            # Process upload
            handler = UploadHandler()
            html_response = handler.handle(session_id, file_data, filename, content_type)

            response = make_response(html_response)
            response.headers['Content-Type'] = 'text/html'
            return response

        # Route D: Health Check (GET /)
        elif request.method == 'GET' and not mode:
            return jsonify({
                'status': 'healthy',
                'service': 'V2V2B Interrogator',
                'version': '1.0.0',
                'endpoints': {
                    'chat_webhook': 'POST /',
                    'upload_ui': 'GET /?mode=ui&session=SESSION_ID',
                    'file_upload': 'POST /?mode=upload&session=SESSION_ID'
                }
            }), 200

        else:
            return jsonify({'error': 'Invalid request'}), 400

    except Exception as e:
        logger.error(f"Unhandled error in entry_point: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
