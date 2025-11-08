"""
Cloud Integration Module - Phase 2
===================================

This module provides services for integrating local Obsidian vaults with
cloud storage and cloud-based LLM services.

Current Components:
------------------
- PathMappingService: Bridges hierarchical local paths with flat cloud storage

Future Components:
-----------------
- GoogleDriveClient: Direct GDrive API integration
- CloudRAGOrchestrator: Hybrid local/cloud RAG coordination
- ConsentManager: User privacy and permission management
- SyncMonitor: Real-time sync status tracking

Key Features:
------------
- O(1) path translation (local ↔ cloud)
- Bidirectional mapping
- Bulk operations for efficiency
- JSON persistence
- Statistics and monitoring

Usage:
------
    from agents.cloud_integration import PathMappingService

    # Initialize service
    service = PathMappingService()

    # Register files
    service.register_file('Projects/Plan.md', 'gdrive_id_123')

    # Translate paths
    gdrive_id = service.resolve_to_gdrive_id('Projects/Plan.md')

Architecture Context:
--------------------
Phase 2 of the AI Executive Assistant Tri-Hybrid architecture focuses on
enabling hybrid local/cloud workflows while maintaining privacy and user control.

    Local Vault → Path Mapping → Cloud Storage → Cloud LLM
        ↑             Service          ↓              ↓
        └──────────── User Privacy Preserved ────────┘
"""

__version__ = "2.0.0"
__phase__ = "Phase 2: Cloud Knowledge Integration"
__status__ = "Path Mapping Core Complete ✅"

from .path_mapping_service import PathMappingService

__all__ = [
    'PathMappingService'
]
