"""Tests for Path Mapping Service."""
import pytest
from services.path_mapping import PathMappingService
from core.models import PathMapping


def test_register_mapping(test_db):
    """Test registering a new path mapping."""
    service = PathMappingService(test_db)

    mapping = service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="abc123",
        cloud_provider="google_drive",
        file_type="markdown"
    )

    assert mapping.local_path == "/vault/test.md"
    assert mapping.cloud_id == "abc123"
    assert mapping.cloud_provider == "google_drive"
    assert mapping.file_type == "markdown"


def test_update_existing_mapping(test_db):
    """Test updating an existing path mapping."""
    service = PathMappingService(test_db)

    # Create initial mapping
    service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="abc123"
    )

    # Update with new cloud_id
    updated = service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="xyz789"
    )

    assert updated.cloud_id == "xyz789"
    assert updated.local_path == "/vault/test.md"


def test_resolve_to_cloud(test_db):
    """Test resolving local path to cloud."""
    service = PathMappingService(test_db)

    service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="abc123"
    )

    result = service.resolve_to_cloud("/vault/test.md")

    assert result is not None
    assert result["cloud_id"] == "abc123"
    assert result["cloud_path"] == "test.md"
    assert result["provider"] == "google_drive"


def test_resolve_to_local(test_db):
    """Test resolving cloud ID to local path."""
    service = PathMappingService(test_db)

    service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="abc123"
    )

    result = service.resolve_to_local("abc123")

    assert result == "/vault/test.md"


def test_resolve_nonexistent_local(test_db):
    """Test resolving non-existent local path."""
    service = PathMappingService(test_db)

    result = service.resolve_to_cloud("/vault/nonexistent.md")

    assert result is None


def test_resolve_nonexistent_cloud(test_db):
    """Test resolving non-existent cloud ID."""
    service = PathMappingService(test_db)

    result = service.resolve_to_local("nonexistent123")

    assert result is None


def test_get_all_mappings(test_db):
    """Test getting all mappings."""
    service = PathMappingService(test_db)

    # Create multiple mappings
    service.register_mapping(
        local_path="/vault/test1.md",
        cloud_path="test1.md",
        cloud_id="abc123"
    )
    service.register_mapping(
        local_path="/vault/test2.md",
        cloud_path="test2.md",
        cloud_id="def456"
    )

    mappings = service.get_all_mappings()

    assert len(mappings) == 2
    assert any(m.local_path == "/vault/test1.md" for m in mappings)
    assert any(m.local_path == "/vault/test2.md" for m in mappings)


def test_delete_mapping(test_db):
    """Test deleting a path mapping."""
    service = PathMappingService(test_db)

    service.register_mapping(
        local_path="/vault/test.md",
        cloud_path="test.md",
        cloud_id="abc123"
    )

    # Delete the mapping
    deleted = service.delete_mapping("/vault/test.md")
    assert deleted is True

    # Verify it's gone
    result = service.resolve_to_cloud("/vault/test.md")
    assert result is None


def test_delete_nonexistent_mapping(test_db):
    """Test deleting a non-existent mapping."""
    service = PathMappingService(test_db)

    deleted = service.delete_mapping("/vault/nonexistent.md")
    assert deleted is False


@pytest.mark.skip(reason="Requires actual vault directory")
def test_sync_vault_mappings(test_db, tmp_path):
    """Test syncing vault mappings."""
    service = PathMappingService(test_db)

    # Create temporary vault structure
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()

    (vault_dir / "test1.md").write_text("# Test 1")
    (vault_dir / "test2.md").write_text("# Test 2")

    projects_dir = vault_dir / "Projects"
    projects_dir.mkdir()
    (projects_dir / "project.md").write_text("# Project")

    # Sync the vault
    count = service.sync_vault_mappings(
        vault_path=str(vault_dir),
        gdrive_folder_id="test_folder_id"
    )

    assert count == 3

    # Check mappings were created
    mappings = service.get_all_mappings()
    assert len(mappings) == 3
