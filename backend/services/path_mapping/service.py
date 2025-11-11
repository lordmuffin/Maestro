"""
Path Mapping Service - Critical middleware for local/cloud sync.

Maintains bidirectional mapping between local file paths and cloud file IDs,
resolving the "path mangling" issue from Google Drive sync plugins.
"""
from typing import Optional, Dict, List
from pathlib import Path
from sqlalchemy.orm import Session
from core.models import PathMapping
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PathMappingService:
    """
    Service for managing local-to-cloud path mappings.

    This is a mission-critical component that enables seamless
    file referencing across the hybrid Data Plane.
    """

    def __init__(self, db: Session):
        """
        Initialize path mapping service.

        Args:
            db: Database session
        """
        self.db = db

    def register_mapping(
        self,
        local_path: str,
        cloud_path: str,
        cloud_id: Optional[str] = None,
        cloud_provider: str = "google_drive",
        file_type: Optional[str] = None
    ) -> PathMapping:
        """
        Register or update a path mapping.

        Args:
            local_path: Local file system path
            cloud_path: Cloud storage path
            cloud_id: Cloud file ID
            cloud_provider: Cloud provider name
            file_type: File type/extension

        Returns:
            Path mapping record
        """
        # Check if mapping exists
        existing = self.db.query(PathMapping).filter(
            PathMapping.local_path == local_path
        ).first()

        if existing:
            # Update existing
            existing.cloud_path = cloud_path
            existing.cloud_id = cloud_id
            existing.cloud_provider = cloud_provider
            existing.file_type = file_type
            existing.last_synced_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated mapping: {local_path} -> {cloud_path}")
            return existing
        else:
            # Create new
            mapping = PathMapping(
                local_path=local_path,
                cloud_path=cloud_path,
                cloud_id=cloud_id,
                cloud_provider=cloud_provider,
                file_type=file_type,
                last_synced_at=datetime.utcnow()
            )
            self.db.add(mapping)
            self.db.commit()
            logger.info(f"Created mapping: {local_path} -> {cloud_path}")
            return mapping

    def resolve_to_cloud(self, local_path: str) -> Optional[Dict[str, str]]:
        """
        Resolve local path to cloud location.

        Args:
            local_path: Local file path

        Returns:
            Dictionary with cloud_path and cloud_id, or None
        """
        mapping = self.db.query(PathMapping).filter(
            PathMapping.local_path == local_path
        ).first()

        if mapping:
            return {
                "cloud_path": mapping.cloud_path,
                "cloud_id": mapping.cloud_id,
                "provider": mapping.cloud_provider
            }
        return None

    def resolve_to_local(self, cloud_id: str) -> Optional[str]:
        """
        Resolve cloud ID to local path.

        Args:
            cloud_id: Cloud file ID

        Returns:
            Local file path, or None
        """
        mapping = self.db.query(PathMapping).filter(
            PathMapping.cloud_id == cloud_id
        ).first()

        return mapping.local_path if mapping else None

    def sync_vault_mappings(
        self,
        vault_path: str,
        gdrive_folder_id: str
    ) -> int:
        """
        Scan vault and create/update mappings for all files.

        This should be run periodically to keep mappings in sync.

        Args:
            vault_path: Path to Obsidian vault
            gdrive_folder_id: Google Drive folder ID

        Returns:
            Number of mappings created/updated
        """
        vault_root = Path(vault_path)
        count = 0

        # Scan all markdown files
        for md_file in vault_root.rglob("*.md"):
            relative_path = str(md_file.relative_to(vault_root))

            # Generate "mangled" cloud path
            # Example: Projects/Nexus/Strategy.md -> Projects_Nexus_Strategy.md
            cloud_path = relative_path.replace("/", "_")

            # Register mapping
            self.register_mapping(
                local_path=str(md_file),
                cloud_path=cloud_path,
                cloud_id=None,  # Will be updated when we query Drive API
                cloud_provider="google_drive",
                file_type="markdown"
            )
            count += 1

        logger.info(f"Synced {count} vault mappings")
        return count

    def get_all_mappings(self) -> List[PathMapping]:
        """Get all path mappings."""
        return self.db.query(PathMapping).all()

    def delete_mapping(self, local_path: str) -> bool:
        """
        Delete a path mapping.

        Args:
            local_path: Local file path

        Returns:
            True if deleted, False if not found
        """
        mapping = self.db.query(PathMapping).filter(
            PathMapping.local_path == local_path
        ).first()

        if mapping:
            self.db.delete(mapping)
            self.db.commit()
            logger.info(f"Deleted mapping: {local_path}")
            return True
        return False
