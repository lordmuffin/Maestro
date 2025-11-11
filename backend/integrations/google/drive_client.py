"""Google Drive client for cloud RAG."""
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Client for Google Drive API operations.

    Handles:
    - File listing and metadata retrieval
    - File content access
    - Folder structure queries
    """

    def __init__(self, credentials_path: str):
        """
        Initialize Google Drive client.

        Args:
            credentials_path: Path to service account JSON
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)

    def list_files(
        self,
        folder_id: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in Drive.

        Args:
            folder_id: Specific folder to list
            query: Custom query string
            page_size: Results per page

        Returns:
            List of file metadata dictionaries
        """
        try:
            # Build query
            if folder_id and not query:
                query = f"'{folder_id}' in parents"

            # Execute request
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields="files(id, name, mimeType, modifiedTime, size, parents)"
            ).execute()

            files = results.get('files', [])
            logger.info(f"Listed {len(files)} files from Drive")
            return files

        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dictionary
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size, parents, webViewLink"
            ).execute()
            return file_metadata
        except HttpError as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise

    def download_file_content(self, file_id: str) -> bytes:
        """
        Download file content.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes
        """
        try:
            # For Google Docs, use export
            metadata = self.get_file_metadata(file_id)
            mime_type = metadata.get('mimeType', '')

            if 'google-apps' in mime_type:
                # Export Google Doc as plain text
                content = self.service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
            else:
                # Download regular file
                content = self.service.files().get_media(
                    fileId=file_id
                ).execute()

            return content

        except HttpError as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def search_files(
        self,
        query_text: str,
        folder_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search files by content or name.

        Args:
            query_text: Search query
            folder_id: Optional folder to limit search

        Returns:
            List of matching files
        """
        # Build search query
        query = f"fullText contains '{query_text}'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        return self.list_files(query=query)
