"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import init_db
from api.routes import health, rag, tasks, cloud_rag, path_mapping
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Maestro AI Executive Assistant",
    description="Unified AI platform with Tri-Hybrid architecture",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting Maestro backend...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(cloud_rag.router, prefix="/api/v1/cloud-rag", tags=["cloud-rag"])
app.include_router(path_mapping.router, prefix="/api/v1/path-mapping", tags=["path-mapping"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Maestro AI Executive Assistant",
        "version": "0.1.0",
        "status": "running",
        "phase": "Phase 2: Cloud Knowledge Integration"
    }
