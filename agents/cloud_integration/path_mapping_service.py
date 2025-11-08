#!/usr/bin/env python3
"""
Path Mapping Service - Phase 2: Cloud Knowledge Integration
============================================================

This service resolves the critical data schema mismatch between local hierarchical
paths (Obsidian vault structure) and flat, mangled paths in Google Drive sync folders.

Problem Statement:
-----------------
When Obsidian vaults are synced to Google Drive using plugins like "Remotely Save",
the hierarchical folder structure is often flattened, and file paths are "mangled"
to create unique flat filenames. For example:

    Local:  Projects/Project_Nexus/Technical_Plan.md
    GDrive: Projects_Project_Nexus_Technical_Plan.md (File ID: 1a2b3c4d5e6f)

This creates a challenge for hybrid RAG systems that need to:
1. Query files locally using hierarchical paths
2. Reference the same files in Google Drive for cloud LLM access
3. Maintain bidirectional translation capability

Solution:
---------
The PathMappingService maintains an in-memory index that maps:
- Local hierarchical paths → Google Drive File IDs + mangled names
- Mangled names → Original local paths (reverse lookup)
- Efficient O(1) lookups for real-time path translation

Use Cases:
----------
1. Hybrid RAG: Local retrieval + cloud LLM generation
2. Sync validation: Verify local and cloud files match
3. Debugging: Trace file references across systems
4. Migration: Bulk path translation for system updates

Architecture Integration:
------------------------
This service is a critical component of Phase 2 (Cloud Integration) in the
AI Executive Assistant Tri-Hybrid architecture:

    Local Obsidian → Path Mapping Service → Google Drive File ID → Cloud LLM
                    ↑                                                  ↓
                    └──────────── Response with references ────────────┘

Author: AI Executive Assistant Team
Version: 1.0.0
Status: Phase 2 - In Progress
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime


class PathMappingService:
    """
    Manages bidirectional mapping between local hierarchical paths and
    Google Drive flat file structure.

    This service maintains an in-memory index of file path translations,
    enabling seamless integration between local and cloud RAG systems.

    Attributes:
        _path_map: Primary index (local_path → cloud metadata)
        _reverse_map: Secondary index (mangled_name → local_path)
        _id_map: Tertiary index (gdrive_file_id → local_path)
    """

    def __init__(self, enable_statistics: bool = True):
        """
        Initialize the Path Mapping Service with empty indices.

        Args:
            enable_statistics: Track usage statistics for monitoring
        """
        # Primary mapping: local_path → {cloud_mangled_name, gdrive_file_id, metadata}
        self._path_map: Dict[str, Dict[str, str]] = {}

        # Reverse mapping: mangled_name → local_path (for debugging/lookups)
        self._reverse_map: Dict[str, str] = {}

        # ID-based mapping: gdrive_file_id → local_path (for cloud→local translation)
        self._id_map: Dict[str, str] = {}

        # Statistics tracking
        self._enable_stats = enable_statistics
        self._stats = {
            "total_files_registered": 0,
            "lookup_count": 0,
            "reverse_lookup_count": 0,
            "id_lookup_count": 0,
            "failed_lookups": 0,
        }

        print("🗺️  Path Mapping Service initialized")
        print("   Ready to bridge local ↔ cloud file references")

    @staticmethod
    def _mangle_path(local_path: str) -> str:
        """
        Simulate the sync plugin's path mangling logic.

        Common mangling patterns:
        - Replace directory separators (/) with underscores (_)
        - Preserve file extension
        - Optional: Handle special characters, spaces, etc.

        Args:
            local_path: Hierarchical local path (e.g., 'Projects/Nexus/Plan.md')

        Returns:
            str: Mangled flat filename (e.g., 'Projects_Nexus_Plan.md')

        Examples:
            >>> PathMappingService._mangle_path('Projects/Nexus/Plan.md')
            'Projects_Nexus_Plan.md'

            >>> PathMappingService._mangle_path('Personal/Journal/2025-11-08.md')
            'Personal_Journal_2025-11-08.md'
        """
        # Normalize path separators (handle both / and \)
        normalized = local_path.replace('\\', '/')

        # Replace directory separators with underscores
        mangled = normalized.replace('/', '_')

        # Additional transformations could include:
        # - Space handling: ' ' → '_'
        # - Special char escaping: '(' → '%28', etc.
        # For now, keep it simple and match common sync plugin behavior

        return mangled

    @staticmethod
    def _unmangle_path(mangled_name: str) -> str:
        """
        Attempt to reverse the mangling process (best-effort).

        Note: This is inherently lossy because multiple hierarchical paths
        could theoretically produce the same mangled name. The service
        uses its index for authoritative reverse lookups.

        Args:
            mangled_name: Flat mangled filename

        Returns:
            str: Best-guess hierarchical path
        """
        # Simple reversal: _ → /
        # This is for debugging only; production should use _reverse_map
        return mangled_name.replace('_', '/')

    def register_file(
        self,
        local_path: str,
        gdrive_id: str,
        additional_metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Register a file mapping in the service.

        This method should be called during:
        1. Initial vault sync (bulk registration)
        2. File creation/modification (incremental updates)
        3. Sync plugin hooks (automated registration)

        Args:
            local_path: Hierarchical path relative to vault root
            gdrive_id: Google Drive File ID (unique identifier)
            additional_metadata: Optional extra data (file size, hash, timestamp, etc.)

        Returns:
            bool: True if registration successful, False if duplicate/error

        Example:
            >>> service = PathMappingService()
            >>> service.register_file(
            ...     'Projects/Nexus/Plan.md',
            ...     '1a2b3c4d5e6f',
            ...     {'size': '2048', 'modified': '2025-11-08T10:30:00Z'}
            ... )
            True
        """
        # Validate inputs
        if not local_path or not gdrive_id:
            print(f"❌ Invalid registration: local_path='{local_path}', gdrive_id='{gdrive_id}'")
            return False

        # Normalize local path (remove leading/trailing slashes)
        local_path = local_path.strip('/')

        # Check for duplicates
        if local_path in self._path_map:
            existing = self._path_map[local_path]
            if existing['gdrive_file_id'] == gdrive_id:
                # Silent update - same file, possibly new metadata
                pass
            else:
                print(f"⚠️  Warning: Overwriting existing mapping for '{local_path}'")
                print(f"   Old GDrive ID: {existing['gdrive_file_id']}")
                print(f"   New GDrive ID: {gdrive_id}")

        # Generate mangled name
        mangled_name = self._mangle_path(local_path)

        # Build metadata
        metadata = {
            'cloud_mangled_name': mangled_name,
            'gdrive_file_id': gdrive_id,
            'registered_at': datetime.now().isoformat(),
        }

        # Add any additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        # Update all three indices
        self._path_map[local_path] = metadata
        self._reverse_map[mangled_name] = local_path
        self._id_map[gdrive_id] = local_path

        # Update statistics
        if self._enable_stats:
            self._stats['total_files_registered'] += 1

        print(f"✅ Registered: {local_path}")
        print(f"   → Mangled: {mangled_name}")
        print(f"   → GDrive ID: {gdrive_id}")

        return True

    def resolve_to_gdrive_id(self, local_path: str) -> Optional[str]:
        """
        Translate a local hierarchical path to Google Drive File ID.

        This is the PRIMARY operation for hybrid RAG systems:
        - Local RAG retrieves context using local paths
        - Cloud LLM needs GDrive File IDs to access files
        - This method bridges the gap

        Args:
            local_path: Local hierarchical path (e.g., 'Projects/Nexus/Plan.md')

        Returns:
            str: Google Drive File ID, or None if not found

        Example:
            >>> service.resolve_to_gdrive_id('Projects/Nexus/Plan.md')
            '1a2b3c4d5e6f'
        """
        # Normalize path
        local_path = local_path.strip('/')

        # Update statistics
        if self._enable_stats:
            self._stats['lookup_count'] += 1

        # Lookup in primary index
        if local_path in self._path_map:
            gdrive_id = self._path_map[local_path]['gdrive_file_id']
            print(f"🔍 Resolved: {local_path} → {gdrive_id}")
            return gdrive_id
        else:
            if self._enable_stats:
                self._stats['failed_lookups'] += 1
            print(f"❌ Not found: {local_path}")
            return None

    def resolve_from_mangled_name(self, mangled_name: str) -> Optional[str]:
        """
        Reverse lookup: Find original local path from mangled filename.

        Useful for:
        - Debugging sync issues
        - Processing GDrive API responses
        - Validating sync completeness

        Args:
            mangled_name: Flat mangled filename (e.g., 'Projects_Nexus_Plan.md')

        Returns:
            str: Original local hierarchical path, or None if not found

        Example:
            >>> service.resolve_from_mangled_name('Projects_Nexus_Plan.md')
            'Projects/Nexus/Plan.md'
        """
        # Update statistics
        if self._enable_stats:
            self._stats['reverse_lookup_count'] += 1

        # Lookup in reverse index
        if mangled_name in self._reverse_map:
            local_path = self._reverse_map[mangled_name]
            print(f"🔍 Reverse resolved: {mangled_name} → {local_path}")
            return local_path
        else:
            if self._enable_stats:
                self._stats['failed_lookups'] += 1
            print(f"❌ Not found: {mangled_name}")
            return None

    def resolve_from_gdrive_id(self, gdrive_id: str) -> Optional[str]:
        """
        Lookup local path using Google Drive File ID.

        Useful when cloud LLM returns file references and you need to
        map them back to local paths for display or further processing.

        Args:
            gdrive_id: Google Drive File ID

        Returns:
            str: Local hierarchical path, or None if not found

        Example:
            >>> service.resolve_from_gdrive_id('1a2b3c4d5e6f')
            'Projects/Nexus/Plan.md'
        """
        # Update statistics
        if self._enable_stats:
            self._stats['id_lookup_count'] += 1

        # Lookup in ID index
        if gdrive_id in self._id_map:
            local_path = self._id_map[gdrive_id]
            print(f"🔍 ID resolved: {gdrive_id} → {local_path}")
            return local_path
        else:
            if self._enable_stats:
                self._stats['failed_lookups'] += 1
            print(f"❌ Not found: {gdrive_id}")
            return None

    def get_mapping_for_path(self, local_path: str) -> Optional[Dict[str, str]]:
        """
        Get complete mapping metadata for a local path.

        Returns all stored information: mangled name, GDrive ID, timestamps, etc.

        Args:
            local_path: Local hierarchical path

        Returns:
            dict: Complete mapping metadata, or None if not found
        """
        local_path = local_path.strip('/')
        return self._path_map.get(local_path)

    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Export all current mappings.

        Useful for:
        - Persistence (save to JSON)
        - Debugging
        - Bulk operations

        Returns:
            dict: Complete path map
        """
        return self._path_map.copy()

    def get_statistics(self) -> Dict[str, int]:
        """
        Get usage statistics.

        Returns:
            dict: Statistics including registration count, lookup counts, etc.
        """
        return self._stats.copy()

    def clear(self):
        """
        Clear all mappings and reset statistics.

        Warning: This is destructive and cannot be undone.
        """
        count = len(self._path_map)
        self._path_map.clear()
        self._reverse_map.clear()
        self._id_map.clear()

        if self._enable_stats:
            self._stats = {
                "total_files_registered": 0,
                "lookup_count": 0,
                "reverse_lookup_count": 0,
                "id_lookup_count": 0,
                "failed_lookups": 0,
            }

        print(f"🧹 Cleared {count} mappings")

    def bulk_register(self, mappings: List[Tuple[str, str, Optional[Dict]]]) -> int:
        """
        Register multiple files at once (efficient for initial sync).

        Args:
            mappings: List of (local_path, gdrive_id, metadata) tuples

        Returns:
            int: Number of files successfully registered

        Example:
            >>> mappings = [
            ...     ('Projects/A.md', 'id1', None),
            ...     ('Projects/B.md', 'id2', {'size': '1024'}),
            ... ]
            >>> service.bulk_register(mappings)
            2
        """
        success_count = 0
        for item in mappings:
            if len(item) == 2:
                local_path, gdrive_id = item
                metadata = None
            else:
                local_path, gdrive_id, metadata = item

            if self.register_file(local_path, gdrive_id, metadata):
                success_count += 1

        print(f"\n📊 Bulk registration complete: {success_count}/{len(mappings)} files")
        return success_count

    def export_to_json(self, filepath: str) -> bool:
        """
        Export all mappings to a JSON file for persistence.

        Args:
            filepath: Path to output JSON file

        Returns:
            bool: True if export successful
        """
        try:
            data = {
                'mappings': self._path_map,
                'statistics': self._stats,
                'exported_at': datetime.now().isoformat(),
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"💾 Exported {len(self._path_map)} mappings to {filepath}")
            return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False

    def import_from_json(self, filepath: str) -> bool:
        """
        Import mappings from a JSON file.

        Args:
            filepath: Path to input JSON file

        Returns:
            bool: True if import successful
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Clear existing data
            self.clear()

            # Import mappings
            mappings = data.get('mappings', {})
            for local_path, metadata in mappings.items():
                gdrive_id = metadata['gdrive_file_id']
                self.register_file(local_path, gdrive_id, metadata)

            print(f"📥 Imported {len(mappings)} mappings from {filepath}")
            return True
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False

    def __len__(self) -> int:
        """Return number of registered files."""
        return len(self._path_map)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"PathMappingService(files={len(self._path_map)}, stats={self._stats})"


def demonstrate_basic_usage():
    """
    Demonstrate basic functionality of the Path Mapping Service.
    """
    print("=" * 80)
    print("PATH MAPPING SERVICE - BASIC DEMONSTRATION")
    print("=" * 80)

    # Initialize service
    service = PathMappingService()

    print("\n[STEP 1] Registering mock files...")
    print("-" * 80)

    # Register sample files (simulating initial vault sync)
    files_to_register = [
        ('Projects/Project_Nexus/Technical_Plan.md', '1a2b3c4d5e6f'),
        ('Projects/Project_Nexus/Budget.md', '2b3c4d5e6f7g'),
        ('Personal/Journal/2025-11-08.md', '3c4d5e6f7g8h'),
    ]

    for local_path, gdrive_id in files_to_register:
        service.register_file(local_path, gdrive_id)

    print("\n[STEP 2] Testing local → GDrive ID resolution...")
    print("-" * 80)

    # Simulate hybrid RAG scenario: Local retrieval identified relevant files
    local_paths_to_resolve = [
        'Projects/Project_Nexus/Technical_Plan.md',
        'Personal/Journal/2025-11-08.md',
        'NonExistent/File.md',  # Test error handling
    ]

    for path in local_paths_to_resolve:
        gdrive_id = service.resolve_to_gdrive_id(path)
        if gdrive_id:
            print(f"✓ Success: Can provide {gdrive_id} to cloud LLM")
        else:
            print(f"✗ Failed: No cloud mapping available")

    print("\n[STEP 3] Testing reverse lookup (mangled → local)...")
    print("-" * 80)

    # Simulate processing GDrive API responses
    mangled_names = [
        'Projects_Project_Nexus_Technical_Plan.md',
        'Personal_Journal_2025-11-08.md',
    ]

    for mangled in mangled_names:
        local_path = service.resolve_from_mangled_name(mangled)
        if local_path:
            print(f"✓ Traced back to local file: {local_path}")

    print("\n[STEP 4] Testing GDrive ID → local resolution...")
    print("-" * 80)

    # Simulate cloud LLM returning file references
    gdrive_ids = ['1a2b3c4d5e6f', '3c4d5e6f7g8h']

    for gid in gdrive_ids:
        local_path = service.resolve_from_gdrive_id(gid)
        if local_path:
            print(f"✓ Cloud reference maps to: {local_path}")

    print("\n[STEP 5] Viewing statistics...")
    print("-" * 80)

    stats = service.get_statistics()
    print("\n📊 Service Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print(f"\n   Total mappings in service: {len(service)}")

    return service


def demonstrate_bulk_operations():
    """
    Demonstrate bulk registration and persistence features.
    """
    print("\n\n" + "=" * 80)
    print("PATH MAPPING SERVICE - BULK OPERATIONS DEMONSTRATION")
    print("=" * 80)

    # Initialize service
    service = PathMappingService()

    print("\n[BULK] Registering multiple files at once...")
    print("-" * 80)

    # Simulate bulk sync of entire vault
    bulk_mappings = [
        ('Projects/ProjectA/Spec.md', 'id_spec_a', {'size': '4096'}),
        ('Projects/ProjectA/Timeline.md', 'id_timeline_a', {'size': '2048'}),
        ('Projects/ProjectB/Overview.md', 'id_overview_b', {'size': '8192'}),
        ('Meetings/2025-11-01-Standup.md', 'id_meeting_1', {'size': '1024'}),
        ('Meetings/2025-11-05-Planning.md', 'id_meeting_2', {'size': '3072'}),
        ('Personal/Ideas/Feature_Brainstorm.md', 'id_ideas_1', {'size': '6144'}),
        ('Personal/Notes/Reading_List.md', 'id_notes_1', {'size': '2560'}),
    ]

    count = service.bulk_register(bulk_mappings)

    print(f"\n✅ Registered {count} files")

    # Demonstrate export
    print("\n[EXPORT] Saving mappings to JSON...")
    print("-" * 80)

    export_path = '/tmp/path_mappings.json'
    if service.export_to_json(export_path):
        print(f"✓ Mappings saved for persistence")

    # Demonstrate import (simulating service restart)
    print("\n[IMPORT] Simulating service restart and reload...")
    print("-" * 80)

    new_service = PathMappingService()
    if new_service.import_from_json(export_path):
        print(f"✓ Restored {len(new_service)} mappings from disk")

        # Verify data integrity
        original_mappings = service.get_all_mappings()
        restored_mappings = new_service.get_all_mappings()

        if original_mappings.keys() == restored_mappings.keys():
            print("✓ Data integrity verified - all paths match")
        else:
            print("✗ Warning: Mismatch in restored data")

    return new_service


def demonstrate_hybrid_rag_scenario():
    """
    Demonstrate a realistic hybrid RAG workflow.
    """
    print("\n\n" + "=" * 80)
    print("PATH MAPPING SERVICE - HYBRID RAG SCENARIO")
    print("=" * 80)

    service = PathMappingService()

    # Setup: Register vault files
    print("\n[SETUP] Registering Obsidian vault (synced to GDrive)...")
    print("-" * 80)

    vault_files = [
        ('Projects/AI_Assistant/Architecture.md', 'gdrive_arch_123'),
        ('Projects/AI_Assistant/Implementation.md', 'gdrive_impl_456'),
        ('Projects/AI_Assistant/Privacy_Design.md', 'gdrive_priv_789'),
    ]

    service.bulk_register(vault_files)

    # Scenario: User asks a question
    print("\n[SCENARIO] User Query: 'Explain the AI Assistant architecture'")
    print("-" * 80)

    # Step 1: Local RAG retrieves relevant files
    print("\n  Step 1: Local RAG Agent identifies relevant files...")
    local_retrieval_results = [
        'Projects/AI_Assistant/Architecture.md',
        'Projects/AI_Assistant/Privacy_Design.md',
    ]
    print(f"  → Local retrieval found {len(local_retrieval_results)} relevant files")

    # Step 2: Path Mapping Service translates to GDrive IDs
    print("\n  Step 2: Translating local paths to GDrive IDs...")
    gdrive_ids = []
    for local_path in local_retrieval_results:
        gdrive_id = service.resolve_to_gdrive_id(local_path)
        if gdrive_id:
            gdrive_ids.append(gdrive_id)

    print(f"  → Translated to {len(gdrive_ids)} GDrive IDs: {gdrive_ids}")

    # Step 3: Cloud LLM processes using GDrive IDs
    print("\n  Step 3: Sending GDrive IDs to cloud LLM (Claude)...")
    print(f"  → Cloud LLM receives: {gdrive_ids}")
    print(f"  → Cloud LLM can access files via Google Drive API")

    # Step 4: Display results with local paths (user-friendly)
    print("\n  Step 4: Presenting results to user...")
    print("\n  📄 Sources used:")
    for local_path in local_retrieval_results:
        print(f"     • {local_path}")

    print("\n✅ Hybrid RAG workflow complete!")
    print("   ✓ Privacy preserved: Only necessary file IDs sent to cloud")
    print("   ✓ User experience: Local paths displayed (familiar structure)")
    print("   ✓ Performance: O(1) path translation overhead")


def main():
    """
    Main execution function with comprehensive demonstrations.
    """
    # Run all demonstrations
    service1 = demonstrate_basic_usage()
    service2 = demonstrate_bulk_operations()
    demonstrate_hybrid_rag_scenario()

    # Final summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n✅ Path Mapping Service - Phase 2 Complete")
    print("\nKey Capabilities Demonstrated:")
    print("  1. ✓ File registration with path mangling")
    print("  2. ✓ Local path → GDrive ID resolution (O(1))")
    print("  3. ✓ Reverse lookup: Mangled name → Local path")
    print("  4. ✓ GDrive ID → Local path translation")
    print("  5. ✓ Bulk operations for efficient vault sync")
    print("  6. ✓ JSON import/export for persistence")
    print("  7. ✓ Statistics and monitoring")
    print("  8. ✓ Hybrid RAG workflow integration")

    print("\n🔗 Integration Points:")
    print("  • Local RAG Agent (Phase 1): Provides local paths")
    print("  • Path Mapping Service (Phase 2): Translates to GDrive IDs")
    print("  • Cloud LLM (Phase 3): Accesses files via GDrive API")

    print("\n📈 Next Steps:")
    print("  → Connect to real Google Drive API")
    print("  → Implement automatic sync detection")
    print("  → Add conflict resolution for path duplicates")
    print("  → Build monitoring dashboard")

    print("\n" + "=" * 80)
    print("All demonstrations completed successfully! 🎉")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
