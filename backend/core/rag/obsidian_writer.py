"""Obsidian vault writing utilities for Maestro."""
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import re

from backend.core.config import settings

logger = logging.getLogger(__name__)


def save_to_obsidian(
    content: str,
    title: Optional[str] = None,
    vault_path: Optional[str] = None,
    subfolder: Optional[str] = None,
    auto_tag: bool = True,
    tag: str = "Maestro"
) -> Path:
    """
    Save content to an Obsidian vault as a markdown file.

    Args:
        content: The markdown content to save
        title: Optional title for the note. If None, uses "Note"
        vault_path: Path to Obsidian vault. If None, uses settings.obsidian_vault_path
        subfolder: Optional subfolder within the vault (e.g., "Meetings", "Notes")
        auto_tag: Whether to automatically append the tag if missing
        tag: Tag to append (default: "Maestro")

    Returns:
        Path: Path to the created file

    Raises:
        ValueError: If vault path doesn't exist or is invalid
        IOError: If file writing fails

    Example:
        >>> path = save_to_obsidian(
        ...     content="# Meeting Notes\\n\\nDiscussed Q4 strategy...",
        ...     title="Q4 Strategy Meeting",
        ...     subfolder="Meetings"
        ... )
        >>> print(path)
        /app/data/vault/Meetings/2025-11-23 - Q4 Strategy Meeting.md
    """
    # Determine vault path
    vault = Path(vault_path or settings.obsidian_vault_path)

    if not vault.exists():
        logger.error(f"Vault path does not exist: {vault}")
        raise ValueError(f"Vault path does not exist: {vault}")

    if not vault.is_dir():
        logger.error(f"Vault path is not a directory: {vault}")
        raise ValueError(f"Vault path is not a directory: {vault}")

    # Determine save directory
    if subfolder:
        save_dir = vault / subfolder
        save_dir.mkdir(parents=True, exist_ok=True)
    else:
        save_dir = vault

    # Generate filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    title_clean = title or "Note"

    # Sanitize title for filename (remove invalid characters)
    title_clean = re.sub(r'[<>:"/\\|?*]', '', title_clean)
    title_clean = title_clean.strip()

    filename = f"{date_str} - {title_clean}.md"
    file_path = save_dir / filename

    # Handle duplicate filenames
    counter = 1
    while file_path.exists():
        filename = f"{date_str} - {title_clean} ({counter}).md"
        file_path = save_dir / filename
        counter += 1

    # Ensure content has the tag if auto_tag is enabled
    final_content = content
    tag_pattern = f"#{tag}"

    if auto_tag:
        # Check if tag already exists in content (either in frontmatter or body)
        if tag_pattern not in content:
            # Add tag at the end if not present
            final_content = f"{content.rstrip()}\n\n{tag_pattern}\n"
        else:
            # Tag already exists, use content as-is
            final_content = content
            logger.info(f"   Tag {tag_pattern} already present in content, skipping auto-append")

    # Write the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        logger.info(f"Successfully saved note to: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise IOError(f"Failed to write file: {e}") from e


def append_to_obsidian(
    content: str,
    file_path: Path,
    separator: str = "\n\n---\n\n"
) -> Path:
    """
    Append content to an existing Obsidian note.

    Args:
        content: Content to append
        file_path: Path to existing note
        separator: Separator to add before new content

    Returns:
        Path: Path to the updated file

    Raises:
        ValueError: If file doesn't exist
        IOError: If file writing fails
    """
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    try:
        # Read existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = f.read()

        # Append new content
        updated = f"{existing.rstrip()}{separator}{content}"

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated)

        logger.info(f"Successfully appended content to: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to append to file {file_path}: {e}")
        raise IOError(f"Failed to append to file: {e}") from e
