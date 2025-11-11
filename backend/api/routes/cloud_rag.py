"""Cloud RAG API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.rag import CloudRAG
from core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Cloud RAG system (singleton)
cloud_rag = None


class CloudRAGQuery(BaseModel):
    """Cloud RAG query request."""
    query: str = Field(..., description="User query text")
    folder_id: Optional[str] = Field(None, description="Google Drive folder ID to limit search")
    max_results: int = Field(5, description="Maximum results", ge=1, le=20)


class CloudSearchRequest(BaseModel):
    """Cloud search request."""
    query: str = Field(..., description="Search query")
    folder_id: Optional[str] = Field(None, description="Folder to limit search")
    max_results: int = Field(10, description="Maximum results", ge=1, le=50)


class CloudRAGResponse(BaseModel):
    """Cloud RAG query response."""
    response: str
    sources: List[Dict[str, Any]]
    query: str


@router.on_event("startup")
async def initialize_cloud_rag():
    """Initialize Cloud RAG system on startup."""
    global cloud_rag

    # Check if credentials are configured
    if not settings.google_application_credentials:
        logger.warning("Google credentials not configured - Cloud RAG disabled")
        return

    if not settings.google_gemini_api_key:
        logger.warning("Gemini API key not configured - Cloud RAG disabled")
        return

    try:
        logger.info("Initializing Cloud RAG system")
        cloud_rag = CloudRAG(
            credentials_path=settings.google_application_credentials,
            gemini_api_key=settings.google_gemini_api_key
        )
        logger.info("Cloud RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Cloud RAG: {e}")


@router.post("/query", response_model=CloudRAGResponse)
async def query_cloud(request: CloudRAGQuery):
    """
    Query Google Drive files using semantic search with Gemini.

    This endpoint:
    1. Searches Google Drive for relevant files
    2. Downloads file contents
    3. Uses Gemini to synthesize an answer with context
    """
    if not cloud_rag:
        raise HTTPException(
            status_code=503,
            detail="Cloud RAG system not initialized. Check Google credentials configuration."
        )

    try:
        result = cloud_rag.hybrid_search(
            query=request.query,
            folder_id=request.folder_id
        )
        return CloudRAGResponse(**result)
    except Exception as e:
        logger.error(f"Cloud query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cloud query failed: {str(e)}"
        )


@router.post("/search")
async def search_drive(request: CloudSearchRequest):
    """
    Search Google Drive files by content or name.

    Args:
        request: Search parameters

    Returns:
        List of matching files
    """
    if not cloud_rag:
        raise HTTPException(
            status_code=503,
            detail="Cloud RAG system not initialized"
        )

    try:
        files = cloud_rag.search_drive(
            query=request.query,
            folder_id=request.folder_id,
            max_results=request.max_results
        )

        return {
            "query": request.query,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"Drive search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/query-files")
async def query_specific_files(
    query: str,
    file_ids: List[str]
):
    """
    Query with specific file IDs as context.

    Args:
        query: User query
        file_ids: List of Google Drive file IDs

    Returns:
        Synthesized response with sources
    """
    if not cloud_rag:
        raise HTTPException(
            status_code=503,
            detail="Cloud RAG system not initialized"
        )

    try:
        result = cloud_rag.query_with_context(
            query=query,
            file_ids=file_ids
        )
        return result
    except Exception as e:
        logger.error(f"Query with files failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.get("/status")
async def get_cloud_rag_status():
    """Get Cloud RAG system status."""
    return {
        "initialized": cloud_rag is not None,
        "google_credentials_configured": settings.google_application_credentials is not None,
        "gemini_api_key_configured": settings.google_gemini_api_key is not None
    }
