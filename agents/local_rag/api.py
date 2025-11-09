"""
FastAPI wrapper for Local RAG Agent
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

app = FastAPI(
    title="Local RAG Agent API",
    description="Privacy-first document retrieval and indexing service",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    llm_provider: Optional[str] = None
    model_tier: Optional[str] = None
    sensitivity: Optional[str] = "medium"

class QueryResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    query: str
    provider_used: str
    model_used: str
    privacy_warning: Optional[str] = None

class IngestRequest(BaseModel):
    vault_path: str
    force_refresh: Optional[bool] = False

class IngestResponse(BaseModel):
    status: str
    message: str
    documents_indexed: int

# Global agent instance
_agent = None

def get_agent():
    """Get the RAG agent instance"""
    return _agent

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG agent at startup"""
    global _agent
    print("\n" + "="*80)
    print("STARTING LOCAL RAG AGENT API")
    print("="*80)
    try:
        from local_rag_agent import LocalRAGAgent
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "/vault")
        print(f"Initializing agent with vault: {vault_path}")
        _agent = LocalRAGAgent(vault_path=vault_path)
        print("✅ Agent initialized successfully at startup")
    except Exception as e:
        print(f"❌ Error initializing agent at startup: {e}")
        import traceback
        traceback.print_exc()
        _agent = None
    print("="*80 + "\n")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Local RAG Agent API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "local-rag"
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the local knowledge base with optional LLM provider and model tier selection
    """
    try:
        import model_registry

        agent = get_agent()
        if agent is None:
            raise HTTPException(status_code=503, detail="RAG agent not initialized")

        # Use defaults if not specified
        provider = request.llm_provider or "local"
        tier = request.model_tier or model_registry.get_default_tier()
        sensitivity = request.sensitivity or "medium"

        # Validate provider availability
        is_available, error_msg = model_registry.check_provider_available(provider)
        if not is_available:
            raise HTTPException(status_code=400, detail=error_msg)

        # Get model for tier
        try:
            model = model_registry.get_model_for_tier(provider, tier)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check for privacy warnings
        should_warn, warning_msg = model_registry.check_privacy_warning(provider, sensitivity)

        # Query the agent with provider/model specification
        results = agent.query(
            request.query,
            top_k=request.top_k,
            llm_provider=provider,
            model=model
        )

        return QueryResponse(
            status="success",
            results=results if isinstance(results, list) else [{"content": str(results)}],
            query=request.query,
            provider_used=provider,
            model_used=model,
            privacy_warning=warning_msg if should_warn else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """
    Ingest documents from Obsidian vault
    """
    try:
        agent = get_agent()
        if agent is None:
            # Try to initialize with new path
            from local_rag_agent import LocalRAGAgent
            agent = LocalRAGAgent(vault_path=request.vault_path)

        # Check if index already exists
        if agent.index is not None and not request.force_refresh:
            return IngestResponse(
                status="success",
                message="Index already exists. Use force_refresh=true to rebuild.",
                documents_indexed=0
            )

        # If no index exists and not forcing refresh, return error
        if agent.index is None and not request.force_refresh:
            return IngestResponse(
                status="error",
                message="No index found. Set force_refresh=true to build index.",
                documents_indexed=0
            )

        # Only ingest if force_refresh is True
        if not request.force_refresh:
            return IngestResponse(
                status="success",
                message="No action taken.",
                documents_indexed=0
            )

        # Perform ingestion and indexing
        if hasattr(agent, 'ingest_documents'):
            count = agent.ingest_documents()
            # Build the vector index after ingesting
            if hasattr(agent, 'build_index') and count > 0:
                agent.build_index()
                # Update the global agent instance
                global _agent
                _agent = agent
        else:
            count = 0

        return IngestResponse(
            status="success",
            message="Documents ingested and indexed successfully",
            documents_indexed=count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get agent statistics"""
    try:
        agent = get_agent()
        if agent is None:
            return {"status": "not_initialized"}

        # Return basic stats
        return {
            "status": "success",
            "agent_type": "LocalRAG",
            "index_status": "ready" if agent else "not_ready"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
