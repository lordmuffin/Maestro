"""Cloud-aware RAG for Google Drive and Workspace files."""
from typing import List, Dict, Any, Optional
from integrations.google.drive_client import GoogleDriveClient
from integrations.google.gemini_client import GeminiClient
import logging

logger = logging.getLogger(__name__)


class CloudRAG:
    """
    Cloud-aware RAG system for Google Drive files.

    Uses:
    - Google Drive API for file access
    - Vertex AI RAG Engine for G-Suite files
    - Gemini for synthesis
    """

    def __init__(
        self,
        credentials_path: str,
        gemini_api_key: str
    ):
        """
        Initialize cloud RAG.

        Args:
            credentials_path: Path to Google service account JSON
            gemini_api_key: Gemini API key
        """
        self.drive_client = GoogleDriveClient(credentials_path)
        self.gemini_client = GeminiClient(gemini_api_key)
        logger.info("Initialized Cloud RAG")

    def search_drive(
        self,
        query: str,
        folder_id: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Google Drive files.

        Args:
            query: Search query
            folder_id: Optional folder to limit search
            max_results: Maximum results

        Returns:
            List of matching files with metadata
        """
        try:
            files = self.drive_client.search_files(query, folder_id)

            # Limit results
            files = files[:max_results]

            logger.info(f"Found {len(files)} files matching query: {query}")
            return files

        except Exception as e:
            logger.error(f"Drive search failed: {e}")
            raise

    def query_with_context(
        self,
        query: str,
        file_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Query with specific file context.

        Args:
            query: User query
            file_ids: List of Google Drive file IDs to use as context

        Returns:
            Response with sources
        """
        try:
            # Download file contents
            contexts = []
            for file_id in file_ids:
                try:
                    content = self.drive_client.download_file_content(file_id)
                    metadata = self.drive_client.get_file_metadata(file_id)

                    contexts.append({
                        "file_id": file_id,
                        "file_name": metadata.get("name", "Unknown"),
                        "content": content.decode('utf-8') if isinstance(content, bytes) else content
                    })
                except Exception as e:
                    logger.warning(f"Failed to load file {file_id}: {e}")

            # Build prompt with context
            context_text = "\n\n".join([
                f"File: {ctx['file_name']}\n{ctx['content']}"
                for ctx in contexts
            ])

            prompt = f"""Based on the following documents, answer the user's question.

Documents:
{context_text}

Question: {query}

Answer:"""

            # Generate response
            response = self.gemini_client.generate(prompt)

            return {
                "response": response,
                "sources": [
                    {"file_id": ctx["file_id"], "file_name": ctx["file_name"]}
                    for ctx in contexts
                ],
                "query": query
            }

        except Exception as e:
            logger.error(f"Query with context failed: {e}")
            raise

    def hybrid_search(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search Drive and synthesize answer.

        Args:
            query: User query
            folder_id: Optional folder to limit search

        Returns:
            Synthesized response
        """
        # Search for relevant files
        files = self.search_drive(query, folder_id, max_results=5)

        if not files:
            return {
                "response": "No relevant files found in Google Drive.",
                "sources": [],
                "query": query
            }

        # Extract file IDs
        file_ids = [f["id"] for f in files]

        # Query with context
        return self.query_with_context(query, file_ids)
