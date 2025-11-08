"""
FastAPI wrapper for Path Mapping Service
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

app = FastAPI(
    title="Path Mapping Service API",
    description="Bridges local hierarchical paths with cloud storage",
    version="1.0.0"
)

class PathRegistrationRequest(BaseModel):
    local_path: str
    cloud_path: str

class PathRegistrationResponse(BaseModel):
    status: str
    local_path: str
    cloud_path: str

class PathResolveRequest(BaseModel):
    path: str
    direction: str = "local_to_cloud"  # or "cloud_to_local"

class PathResolveResponse(BaseModel):
    status: str
    original_path: str
    resolved_path: Optional[str]
    direction: str

# Global service instance
_service = None

def get_service():
    """Lazy load the path mapping service"""
    global _service
    if _service is None:
        try:
            from path_mapping_service import PathMappingService
            mappings_file = os.getenv("MAPPINGS_FILE", "/app/data/path_mappings.json")
            _service = PathMappingService(mappings_file=mappings_file)
        except Exception as e:
            print(f"Error initializing service: {e}")
            _service = None
    return _service

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Path Mapping Service API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "path-mapping"
    }

@app.post("/register", response_model=PathRegistrationResponse)
async def register_path(request: PathRegistrationRequest):
    """
    Register a new path mapping
    """
    try:
        service = get_service()
        if service is None:
            raise HTTPException(status_code=503, detail="Path mapping service not initialized")

        # Register the mapping
        service.register_mapping(request.local_path, request.cloud_path)

        return PathRegistrationResponse(
            status="success",
            local_path=request.local_path,
            cloud_path=request.cloud_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resolve", response_model=PathResolveResponse)
async def resolve_path(request: PathResolveRequest):
    """
    Resolve a path from local to cloud or vice versa
    """
    try:
        service = get_service()
        if service is None:
            raise HTTPException(status_code=503, detail="Path mapping service not initialized")

        # Resolve the path
        if request.direction == "local_to_cloud":
            resolved = service.resolve_local_to_cloud(request.path)
        elif request.direction == "cloud_to_local":
            resolved = service.resolve_cloud_to_local(request.path)
        else:
            raise HTTPException(status_code=400, detail="Invalid direction. Use 'local_to_cloud' or 'cloud_to_local'")

        return PathResolveResponse(
            status="success" if resolved else "not_found",
            original_path=request.path,
            resolved_path=resolved,
            direction=request.direction
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mappings")
async def get_all_mappings():
    """Get all registered path mappings"""
    try:
        service = get_service()
        if service is None:
            raise HTTPException(status_code=503, detail="Path mapping service not initialized")

        # Get all mappings
        if hasattr(service, 'get_all_mappings'):
            mappings = service.get_all_mappings()
        else:
            mappings = {}

        return {
            "status": "success",
            "mappings": mappings,
            "count": len(mappings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
