"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
import httpx
from core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint.
    
    Returns:
        Health status of main components
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "ollama": "unknown"
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_host}/api/tags",
                timeout=5.0
            )
            if response.status_code == 200:
                health_status["ollama"] = "healthy"
            else:
                health_status["ollama"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        health_status["ollama"] = f"unhealthy: {str(e)}"
        # Don't mark as degraded since Ollama is optional in Phase 1
    
    return health_status


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with component versions."""
    return {
        "components": {
            "backend": {
                "status": "healthy",
                "version": "0.1.0",
                "phase": "Phase 1"
            },
            "ollama": {
                "host": settings.ollama_host,
                "model": settings.ollama_model
            },
            "features": {
                "proactive_suggestions": settings.enable_proactive_suggestions,
                "hitl_confirmations": settings.enable_hitl_confirmations,
                "local_rag": True,
                "cloud_integration": False  # Phase 2
            }
        }
    }
