"""Path mapping API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from core.database import get_db
from services.path_mapping import PathMappingService

router = APIRouter()


class PathMappingCreate(BaseModel):
    """Path mapping creation request."""
    local_path: str = Field(..., description="Local file path")
    cloud_path: str = Field(..., description="Cloud storage path")
    cloud_id: Optional[str] = Field(None, description="Cloud file ID")
    cloud_provider: str = Field("google_drive", description="Cloud provider")
    file_type: Optional[str] = Field(None, description="File type")


class PathMappingResponse(BaseModel):
    """Path mapping response."""
    id: str
    local_path: str
    cloud_path: str
    cloud_id: Optional[str]
    cloud_provider: str
    file_type: Optional[str]
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncVaultRequest(BaseModel):
    """Vault sync request."""
    vault_path: str = Field(..., description="Path to Obsidian vault")
    gdrive_folder_id: str = Field(..., description="Google Drive folder ID")


@router.post("", response_model=PathMappingResponse)
async def create_mapping(
    mapping: PathMappingCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update a path mapping.

    This endpoint registers a bidirectional mapping between
    a local file path and its cloud equivalent.
    """
    service = PathMappingService(db)

    result = service.register_mapping(
        local_path=mapping.local_path,
        cloud_path=mapping.cloud_path,
        cloud_id=mapping.cloud_id,
        cloud_provider=mapping.cloud_provider,
        file_type=mapping.file_type
    )

    return result


@router.get("", response_model=List[PathMappingResponse])
async def list_mappings(db: Session = Depends(get_db)):
    """List all path mappings."""
    service = PathMappingService(db)
    mappings = service.get_all_mappings()
    return mappings


@router.get("/resolve/local/{path:path}")
async def resolve_local_to_cloud(
    path: str,
    db: Session = Depends(get_db)
):
    """
    Resolve local path to cloud location.

    Args:
        path: Local file path

    Returns:
        Cloud location details
    """
    service = PathMappingService(db)
    result = service.resolve_to_cloud(path)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No mapping found for path: {path}"
        )

    return result


@router.get("/resolve/cloud/{cloud_id}")
async def resolve_cloud_to_local(
    cloud_id: str,
    db: Session = Depends(get_db)
):
    """
    Resolve cloud ID to local path.

    Args:
        cloud_id: Cloud file ID

    Returns:
        Local file path
    """
    service = PathMappingService(db)
    result = service.resolve_to_local(cloud_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No mapping found for cloud ID: {cloud_id}"
        )

    return {"local_path": result}


@router.post("/sync")
async def sync_vault(
    request: SyncVaultRequest,
    db: Session = Depends(get_db)
):
    """
    Sync vault and create mappings for all files.

    This scans the Obsidian vault and creates/updates mappings
    for all markdown files.
    """
    service = PathMappingService(db)

    try:
        count = service.sync_vault_mappings(
            vault_path=request.vault_path,
            gdrive_folder_id=request.gdrive_folder_id
        )

        return {
            "status": "success",
            "mappings_synced": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vault sync failed: {str(e)}"
        )


@router.delete("/{local_path:path}")
async def delete_mapping(
    local_path: str,
    db: Session = Depends(get_db)
):
    """Delete a path mapping."""
    service = PathMappingService(db)
    deleted = service.delete_mapping(local_path)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No mapping found for path: {local_path}"
        )

    return {"status": "deleted", "local_path": local_path}
