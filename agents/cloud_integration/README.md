# Path Mapping Service - Phase 2: Cloud Knowledge Integration

## Overview

The Path Mapping Service solves a critical data schema mismatch in hybrid local/cloud RAG systems: bridging hierarchical local paths (Obsidian vaults) with flat, mangled paths in cloud storage (Google Drive).

## The Problem

When Obsidian vaults are synced to Google Drive using plugins like "Remotely Save", the folder structure is often flattened:

```
Local Path (Hierarchical):
  Projects/
    Project_Nexus/
      Technical_Plan.md
      Budget.md

Google Drive (Flat, Mangled):
  Projects_Project_Nexus_Technical_Plan.md  (File ID: 1a2b3c4d5e6f)
  Projects_Project_Nexus_Budget.md          (File ID: 2b3c4d5e6f7g)
```

This creates challenges for hybrid RAG systems:
1. **Local RAG** retrieves documents using hierarchical paths
2. **Cloud LLM** needs Google Drive File IDs to access files
3. **User Experience** requires showing familiar local paths

## The Solution

PathMappingService maintains a bidirectional index enabling O(1) translations:

```python
# Local → Cloud
gdrive_id = service.resolve_to_gdrive_id('Projects/Nexus/Plan.md')
# Returns: '1a2b3c4d5e6f'

# Cloud → Local
local_path = service.resolve_from_gdrive_id('1a2b3c4d5e6f')
# Returns: 'Projects/Nexus/Plan.md'

# Mangled → Local (for debugging)
local_path = service.resolve_from_mangled_name('Projects_Nexus_Plan.md')
# Returns: 'Projects/Nexus/Plan.md'
```

## Architecture

### Data Model

Three synchronized indices for efficient lookups:

```python
# Primary: Local → Cloud metadata
_path_map = {
    'Projects/Nexus/Plan.md': {
        'cloud_mangled_name': 'Projects_Nexus_Plan.md',
        'gdrive_file_id': '1a2b3c4d5e6f',
        'registered_at': '2025-11-08T10:30:00Z',
        # ... additional metadata
    }
}

# Reverse: Mangled → Local
_reverse_map = {
    'Projects_Nexus_Plan.md': 'Projects/Nexus/Plan.md'
}

# ID-based: GDrive ID → Local
_id_map = {
    '1a2b3c4d5e6f': 'Projects/Nexus/Plan.md'
}
```

### Performance

- **Space Complexity**: O(3n) - Three indices, n files
- **Time Complexity**: O(1) for all lookup operations
- **Memory Usage**: ~100 bytes per file (typical)

For a 1,000 file vault: ~100KB memory usage

## Usage

### Basic Setup

```python
from path_mapping_service import PathMappingService

# Initialize service
service = PathMappingService()

# Register files (typically done during initial sync)
service.register_file(
    local_path='Projects/Nexus/Plan.md',
    gdrive_id='1a2b3c4d5e6f',
    additional_metadata={'size': '2048', 'hash': 'abc123'}
)
```

### Hybrid RAG Workflow

```python
# Step 1: Local RAG identifies relevant files
local_paths = local_rag_agent.query("Explain the architecture")
# Returns: ['Projects/AI_Assistant/Architecture.md', ...]

# Step 2: Translate to GDrive IDs
gdrive_ids = [
    service.resolve_to_gdrive_id(path)
    for path in local_paths
]

# Step 3: Send to cloud LLM
response = claude_api.generate(
    prompt="Explain the architecture",
    file_ids=gdrive_ids  # Cloud can access via GDrive API
)

# Step 4: Display with local paths (user-friendly)
print("Sources used:")
for path in local_paths:
    print(f"  • {path}")
```

### Bulk Operations

```python
# Initial vault sync
mappings = [
    ('Projects/A.md', 'id1', {'size': '1024'}),
    ('Projects/B.md', 'id2', {'size': '2048'}),
    # ... hundreds more
]

count = service.bulk_register(mappings)
print(f"Registered {count} files")
```

### Persistence

```python
# Save mappings (before shutdown)
service.export_to_json('/path/to/mappings.json')

# Load mappings (after restart)
service = PathMappingService()
service.import_from_json('/path/to/mappings.json')
```

## API Reference

### Core Methods

#### `register_file(local_path, gdrive_id, additional_metadata=None)`

Register a single file mapping.

**Parameters:**
- `local_path` (str): Hierarchical path relative to vault root
- `gdrive_id` (str): Google Drive File ID
- `additional_metadata` (dict, optional): Extra data (size, hash, timestamp, etc.)

**Returns:** `bool` - True if successful

**Example:**
```python
service.register_file(
    'Projects/Nexus/Plan.md',
    '1a2b3c4d5e6f',
    {'size': '2048', 'modified': '2025-11-08T10:30:00Z'}
)
```

#### `resolve_to_gdrive_id(local_path)`

PRIMARY operation: Translate local path to Google Drive File ID.

**Parameters:**
- `local_path` (str): Local hierarchical path

**Returns:** `str` or `None` - GDrive File ID if found

**Example:**
```python
gdrive_id = service.resolve_to_gdrive_id('Projects/Nexus/Plan.md')
# Returns: '1a2b3c4d5e6f'
```

#### `resolve_from_mangled_name(mangled_name)`

Reverse lookup: Find original path from mangled filename.

**Parameters:**
- `mangled_name` (str): Flat mangled filename

**Returns:** `str` or `None` - Local path if found

**Example:**
```python
local_path = service.resolve_from_mangled_name('Projects_Nexus_Plan.md')
# Returns: 'Projects/Nexus/Plan.md'
```

#### `resolve_from_gdrive_id(gdrive_id)`

Lookup local path from Google Drive File ID.

**Parameters:**
- `gdrive_id` (str): Google Drive File ID

**Returns:** `str` or `None` - Local path if found

**Example:**
```python
local_path = service.resolve_from_gdrive_id('1a2b3c4d5e6f')
# Returns: 'Projects/Nexus/Plan.md'
```

#### `bulk_register(mappings)`

Register multiple files efficiently.

**Parameters:**
- `mappings` (list): List of (local_path, gdrive_id, metadata) tuples

**Returns:** `int` - Number successfully registered

**Example:**
```python
mappings = [
    ('Projects/A.md', 'id1', None),
    ('Projects/B.md', 'id2', {'size': '1024'}),
]
count = service.bulk_register(mappings)
```

### Utility Methods

#### `get_mapping_for_path(local_path)`
Get complete metadata for a path.

#### `get_all_mappings()`
Export all mappings as dict.

#### `get_statistics()`
Get usage statistics (lookups, registrations, etc.).

#### `export_to_json(filepath)`
Save mappings to JSON file.

#### `import_from_json(filepath)`
Load mappings from JSON file.

#### `clear()`
Clear all mappings (destructive).

#### `__len__()`
Returns number of registered files.

## Testing

Run the comprehensive demonstration:

```bash
python path_mapping_service.py
```

This runs three demonstrations:
1. **Basic Usage**: Registration and lookup operations
2. **Bulk Operations**: Bulk registration and persistence
3. **Hybrid RAG Scenario**: Realistic end-to-end workflow

## Integration with AI Executive Assistant

### Phase 1: Local RAG Agent
Local-only processing using hierarchical paths.

### Phase 2: Path Mapping Service ✅ (Current)
Bridges local and cloud file references.

### Phase 3: Cloud Integration (Next)
Use resolved GDrive IDs to enable cloud LLM access to vault files.

### Workflow
```
User Query
    ↓
[Local RAG Agent] → Retrieves relevant files (local paths)
    ↓
[Path Mapping Service] → Translates to GDrive IDs
    ↓
[Cloud LLM] → Accesses files via GDrive API
    ↓
[Response] → Displayed with local paths (user-friendly)
```

## Path Mangling Logic

Current implementation uses simple mangling:
```python
'Projects/Nexus/Plan.md' → 'Projects_Nexus_Plan.md'
```

The `_mangle_path()` method can be extended for:
- Space handling: `' '` → `'_'`
- Special characters: URL encoding
- Custom sync plugin logic

## Limitations

1. **In-Memory Only**: Mappings not persisted automatically (use `export_to_json()`)
2. **No Sync Detection**: Manual registration required (future: watch file system)
3. **Simple Mangling**: Assumes `'/'` → `'_'` pattern (extend for other plugins)
4. **No Conflict Resolution**: Duplicate paths overwrite existing entries
5. **No GDrive Integration**: File IDs are simulated (future: real GDrive API)

## Future Enhancements

### Automatic Sync Detection
Monitor file system and GDrive for changes, auto-register new files.

### Persistent Storage
SQLite database for durable storage (current: JSON export/import).

### Conflict Resolution
Handle edge cases:
- Multiple files with same name
- Path collisions after mangling
- Sync plugin version differences

### Real GDrive Integration
```python
# Future implementation
service = PathMappingService(gdrive_client=gdrive_api)
service.sync_with_drive()  # Auto-discover and register all files
```

### Monitoring Dashboard
Real-time visualization of:
- Sync status
- Mapping coverage
- Lookup performance
- Error rates

## Troubleshooting

### File Not Found Error

**Problem:** `resolve_to_gdrive_id()` returns `None`

**Solutions:**
1. Verify file is registered: `service.get_mapping_for_path(path)`
2. Check path normalization: Remove leading/trailing slashes
3. Confirm sync completed: Check GDrive folder

### Import/Export Issues

**Problem:** JSON import fails

**Solutions:**
1. Validate JSON structure
2. Check file permissions
3. Verify file path exists

### Performance Degradation

**Problem:** Slow lookups with many files

**Analysis:**
- Current: O(1) lookups should be fast
- If slow: Check Python dict implementation (rare)
- If memory constrained: Use persistent storage (SQLite)

## Best Practices

1. **Register Early**: Populate mappings during initial sync
2. **Persist Regularly**: Export to JSON periodically
3. **Monitor Statistics**: Track failed lookups to identify issues
4. **Validate Mappings**: Periodically verify local and cloud files match
5. **Handle Errors**: Always check for `None` returns from resolve methods

## Contributing

Phase 2 contributions welcome:

1. **Sync Integration**: Connect to real Google Drive API
2. **Alternative Mangling**: Support other sync plugins (Obsidian Sync, etc.)
3. **Performance**: Optimize for very large vaults (100k+ files)
4. **Monitoring**: Build dashboard for sync status

## References

- [Google Drive API](https://developers.google.com/drive/api/v3/about-sdk)
- [Obsidian Remotely Save Plugin](https://github.com/remotely-save/remotely-save)
- [Path Normalization Best Practices](https://docs.python.org/3/library/pathlib.html)

## License

[Specify License]

---

**Status**: Phase 2 - Path Mapping Core Complete ✅
**Next**: Phase 3 - Real GDrive API Integration
**Last Updated**: 2025-11-08
