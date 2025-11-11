"""Knowledge Search EA Skill - Semantic search across vault."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import logging

from .base import EASkill, SkillCategory

logger = logging.getLogger(__name__)


class SearchFormat(str, Enum):
    """Search result formats."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    RAW = "raw"


class KnowledgeSearchInput(BaseModel):
    """Input schema for Knowledge Search skill."""

    query: str = Field(
        ...,
        description="Natural language search query for the knowledge base",
        min_length=1
    )
    search_scope: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of folders or tags to limit search scope. "
            "If None, searches entire vault."
        )
    )
    result_format: SearchFormat = Field(
        default=SearchFormat.SUMMARY,
        description="Format for search results: summary, detailed, or raw"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )


class SearchKnowledgeBaseSkill(EASkill):
    """
    Search the Obsidian knowledge base using semantic search.

    This skill uses the Local RAG system to perform privacy-preserving
    semantic search across the vault. No data leaves the local machine.
    """

    name = "search_knowledge_base"
    description = (
        "Search your Obsidian vault for relevant documents and notes. "
        "Uses semantic search (not just keyword matching) to find the "
        "most relevant information. Can be scoped to specific folders or tags."
    )
    category = SkillCategory.RETRIEVAL
    input_schema = KnowledgeSearchInput

    # Privacy-first: only local LLM
    supports_local = True
    supports_gemini = False
    supports_claude = False

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute knowledge base search.

        Returns:
            Dictionary with search results
        """
        logger.info(f"Searching knowledge base with query: {kwargs.get('query')}")

        # Validate input
        validated = self.validate_parameters(**kwargs)

        query = validated.query
        scope = validated.search_scope
        format = validated.result_format
        max_results = validated.max_results

        # Perform search (placeholder - would integrate with ObsidianRAG)
        results = await self._perform_search(query, scope, max_results)

        # Format results
        formatted_results = self._format_results(results, format)

        return {
            "success": True,
            "query": query,
            "results_found": len(results),
            "max_results": max_results,
            "search_scope": scope or ["entire_vault"],
            "result_format": format.value,
            "results": formatted_results
        }

    async def _perform_search(
        self,
        query: str,
        scope: Optional[List[str]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.

        In production, this would integrate with ObsidianRAG from Phase 1.
        """
        # Placeholder results
        return [
            {
                "file_path": "Projects/AI_Assistant/Architecture.md",
                "title": "AI Assistant Architecture",
                "relevance_score": 0.95,
                "excerpt": "The tri-hybrid architecture combines local-first privacy with cloud integration...",
                "tags": ["#architecture", "#ai"],
                "created_date": "2025-01-01",
                "modified_date": "2025-01-10"
            },
            {
                "file_path": "Meetings/2025-01-08_Team_Sync.md",
                "title": "Team Sync - Jan 8",
                "relevance_score": 0.87,
                "excerpt": "Discussed AI assistant progress and Phase 3 implementation...",
                "tags": ["#meeting", "#team"],
                "created_date": "2025-01-08",
                "modified_date": "2025-01-08"
            },
            {
                "file_path": "Ideas/AI_Features.md",
                "title": "AI Feature Ideas",
                "relevance_score": 0.82,
                "excerpt": "Brainstorming session on potential AI assistant features...",
                "tags": ["#ideas", "#ai"],
                "created_date": "2024-12-15",
                "modified_date": "2025-01-05"
            }
        ][:max_results]

    def _format_results(
        self,
        results: List[Dict[str, Any]],
        format: SearchFormat
    ) -> List[Dict[str, Any]]:
        """Format search results according to requested format."""
        if format == SearchFormat.SUMMARY:
            return [
                {
                    "title": r["title"],
                    "file_path": r["file_path"],
                    "relevance": f"{r['relevance_score']:.0%}"
                }
                for r in results
            ]

        elif format == SearchFormat.DETAILED:
            return [
                {
                    "title": r["title"],
                    "file_path": r["file_path"],
                    "relevance": f"{r['relevance_score']:.0%}",
                    "excerpt": r["excerpt"],
                    "tags": r["tags"],
                    "modified": r["modified_date"]
                }
                for r in results
            ]

        else:  # RAW
            return results
