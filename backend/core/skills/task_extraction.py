"""Task Extraction EA Skill - Extract actionable tasks from notes."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from .base import EASkill, SkillCategory

logger = logging.getLogger(__name__)


class TaskExtractionInput(BaseModel):
    """Input schema for Task Extraction skill."""

    source_file: Optional[str] = Field(
        default=None,
        description="Specific file to extract tasks from (if None, scans recent notes)"
    )
    lookback_days: int = Field(
        default=7,
        description="Number of days to look back for notes (if source_file is None)",
        ge=1,
        le=90
    )
    priority_threshold: str = Field(
        default="low",
        description="Minimum priority level to extract: low, medium, high, urgent"
    )
    auto_create_tasks: bool = Field(
        default=False,
        description="Automatically create tasks in the task system"
    )


class ExtractTasksSkill(EASkill):
    """
    Extract actionable tasks from notes and documents.

    This skill uses NLP to identify:
    - TODO items ([ ] syntax)
    - Action items in meeting notes
    - Deadlines and due dates
    - Implicit tasks from context

    Can optionally create tasks automatically in the task system.
    """

    name = "extract_tasks"
    description = (
        "Extract actionable tasks from your notes and meeting documents. "
        "Identifies TODO items, action items, and implicit tasks with deadlines. "
        "Can automatically create tasks in your task management system."
    )
    category = SkillCategory.ANALYSIS
    input_schema = TaskExtractionInput

    # Works with local for privacy, but benefits from Gemini's NLP
    supports_local = True
    supports_gemini = True  # Preferred for NLP
    supports_claude = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute task extraction.

        Returns:
            Dictionary with extracted tasks
        """
        logger.info(f"Extracting tasks with params: {kwargs}")

        # Validate input
        validated = self.validate_parameters(**kwargs)

        source_file = validated.source_file
        lookback_days = validated.lookback_days
        priority_threshold = validated.priority_threshold
        auto_create = validated.auto_create_tasks

        # Extract tasks
        if source_file:
            tasks = await self._extract_from_file(source_file, priority_threshold)
        else:
            tasks = await self._extract_from_recent_notes(lookback_days, priority_threshold)

        # Optionally create tasks
        created_tasks = []
        if auto_create:
            created_tasks = await self._create_tasks(tasks)

        return {
            "success": True,
            "tasks_found": len(tasks),
            "tasks_extracted": tasks,
            "auto_created": auto_create,
            "created_task_ids": created_tasks,
            "source": source_file or f"last_{lookback_days}_days",
            "priority_threshold": priority_threshold
        }

    async def _extract_from_file(
        self,
        file_path: str,
        priority_threshold: str
    ) -> List[Dict[str, Any]]:
        """Extract tasks from a specific file."""
        logger.info(f"Extracting tasks from file: {file_path}")

        # Placeholder - would parse file and use NLP
        return [
            {
                "text": "Review and merge PR #123",
                "priority": "high",
                "source": file_path,
                "line_number": 15,
                "due_date": "2025-01-15",
                "context": "Code review needed for authentication feature"
            },
            {
                "text": "Update documentation with new API endpoints",
                "priority": "medium",
                "source": file_path,
                "line_number": 42,
                "due_date": None,
                "context": "API docs are outdated"
            }
        ]

    async def _extract_from_recent_notes(
        self,
        lookback_days: int,
        priority_threshold: str
    ) -> List[Dict[str, Any]]:
        """Extract tasks from recent notes."""
        logger.info(f"Extracting tasks from last {lookback_days} days")

        # Placeholder - would scan recent notes
        return [
            {
                "text": "Prepare Q1 budget presentation",
                "priority": "high",
                "source": "Meetings/2025-01-08_Leadership.md",
                "line_number": 28,
                "due_date": "2025-01-20",
                "context": "Leadership meeting action item"
            },
            {
                "text": "Schedule team building event",
                "priority": "medium",
                "source": "Ideas/Team_Events.md",
                "line_number": 5,
                "due_date": "2025-02-01",
                "context": "Q1 team event planning"
            },
            {
                "text": "Research new AI tools",
                "priority": "low",
                "source": "Daily/2025-01-09.md",
                "line_number": 12,
                "due_date": None,
                "context": "Competitive analysis"
            }
        ]

    async def _create_tasks(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Create tasks in the task management system.

        In production, this would integrate with the tasks API from Phase 1.
        """
        logger.info(f"Creating {len(tasks)} tasks")

        # Placeholder - would call tasks API
        task_ids = [f"task_{i:04d}" for i in range(len(tasks))]

        return task_ids
