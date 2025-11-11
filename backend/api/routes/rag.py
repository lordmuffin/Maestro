"""RAG query endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.rag import ObsidianRAG
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize RAG system (singleton)
obsidian_rag = None


class RAGQuery(BaseModel):
    """RAG query request."""
    query: str = Field(..., description="User query text")
    similarity_top_k: int = Field(5, description="Number of similar chunks", ge=1, le=20)
    user_id: Optional[str] = Field(None, description="User identifier")


class RAGResponse(BaseModel):
    """RAG query response."""
    response: str
    sources: List[Dict[str, Any]]
    query: str


class IndexRequest(BaseModel):
    """Vault indexing request."""
    force_reload: bool = Field(False, description="Force re-indexing")


@router.on_event("startup")
async def initialize_rag():
    """Initialize RAG system on startup."""
    global obsidian_rag
    try:
        logger.info("Initializing Obsidian RAG system")
        obsidian_rag = ObsidianRAG()
        obsidian_rag.load_vault()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG: {e}")


@router.post("/query", response_model=RAGResponse)
async def query_vault(request: RAGQuery):
    """
    Query the Obsidian vault using semantic search.
    
    This endpoint performs privacy-preserving RAG:
    1. Embeds query using local Ollama
    2. Searches local vector index
    3. Generates response using local LLM
    
    No data leaves the local machine.
    """
    if not obsidian_rag:
        raise HTTPException(
            status_code=503,
            detail="RAG system not initialized"
        )
    
    try:
        result = obsidian_rag.query(
            query_text=request.query,
            similarity_top_k=request.similarity_top_k
        )
        return RAGResponse(**result)
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/index")
async def index_vault(
    request: IndexRequest,
    background_tasks: BackgroundTasks
):
    """
    Index or re-index the Obsidian vault.
    
    This is a long-running operation that will be executed in the background.
    """
    if not obsidian_rag:
        raise HTTPException(
            status_code=503,
            detail="RAG system not initialized"
        )
    
    def index_task():
        try:
            obsidian_rag.load_vault(force_reload=request.force_reload)
            logger.info("Vault indexing completed")
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
    
    background_tasks.add_task(index_task)
    
    return {
        "status": "indexing_started",
        "force_reload": request.force_reload
    }


@router.get("/graph/{file_path:path}")
async def get_graph_context(file_path: str):
    """
    Get graph context for a file (backlinks, outlinks, tags).
    
    Args:
        file_path: Path to file relative to vault root
    """
    if not obsidian_rag:
        raise HTTPException(
            status_code=503,
            detail="RAG system not initialized"
        )
    
    try:
        context = obsidian_rag.get_graph_context(file_path)
        return context
    except Exception as e:
        logger.error(f"Failed to get graph context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph context: {str(e)}"
        )


@router.get("/search/tag/{tag}")
async def search_by_tag(tag: str, limit: int = 10):
    """
    Search vault by tag.
    
    Args:
        tag: Tag to search for (without #)
        limit: Maximum results
    """
    if not obsidian_rag:
        raise HTTPException(
            status_code=503,
            detail="RAG system not initialized"
        )
    
    try:
        results = obsidian_rag.search_by_tag(tag, limit=limit)
        return {
            "tag": tag,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Tag search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
