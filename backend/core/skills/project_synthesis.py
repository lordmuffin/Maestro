"""Project Synthesis EA Skill - Generate comprehensive project overviews."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from .base import EASkill, SkillCategory

logger = logging.getLogger(__name__)


class ProjectSynthesisInput(BaseModel):
    """Input schema for Project Synthesis skill."""

    project_name: str = Field(
        ...,
        description=(
            "The name of the project to synthesize. Should match a project "
            "folder or tag in your Obsidian vault (e.g., 'Project_Nexus', "
            "'AI_Assistant'). Case-sensitive."
        ),
        min_length=1
    )
    output_format: str = Field(
        default="markdown",
        description=(
            "The desired output format for the synthesis. Options: "
            "'markdown' (default, for documents), 'json' (for structured data), "
            "'html' (for web display), 'executive_summary' (brief overview)."
        )
    )
    include_timeline: bool = Field(
        default=True,
        description="Include chronological timeline of project evolution"
    )
    include_related: bool = Field(
        default=True,
        description="Include related projects and dependencies"
    )


class GenerateProjectSynthesisSkill(EASkill):
    """
    Generate comprehensive project synthesis from vault documents.

    This skill combines:
    - Phase 1: Local RAG for document retrieval
    - Phase 2: Path Mapping for cloud file access
    - Phase 3: Orchestrator for routing to appropriate LLM

    Produces structured overviews including:
    - Project goals and status
    - Key milestones and timeline
    - Team members and stakeholders
    - Related documents and links
    - Next steps and blockers
    """

    name = "generate_project_synthesis"
    description = (
        "Generate a comprehensive synthesis of all notes, documents, and "
        "information related to a specific project in your Obsidian vault. "
        "Useful for creating project overviews, status reports, or "
        "understanding project evolution over time. Includes timeline, "
        "stakeholders, and related projects."
    )
    category = SkillCategory.SYNTHESIS
    input_schema = ProjectSynthesisInput

    # Best with Claude for long-context synthesis
    supports_local = True
    supports_gemini = True
    supports_claude = True  # Preferred

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute project synthesis.

        Returns:
            Dictionary with synthesis content
        """
        logger.info(f"Generating project synthesis for: {kwargs.get('project_name')}")

        # Validate input
        validated = self.validate_parameters(**kwargs)

        project_name = validated.project_name
        output_format = validated.output_format
        include_timeline = validated.include_timeline
        include_related = validated.include_related

        # Gather project documents
        documents = await self._gather_project_documents(project_name)

        # Extract project metadata
        metadata = await self._extract_project_metadata(documents)

        # Generate timeline if requested
        timeline = None
        if include_timeline:
            timeline = await self._generate_timeline(documents)

        # Find related projects if requested
        related_projects = None
        if include_related:
            related_projects = await self._find_related_projects(project_name, documents)

        # Synthesize into requested format
        synthesis = self._synthesize_output(
            project_name=project_name,
            metadata=metadata,
            documents=documents,
            timeline=timeline,
            related_projects=related_projects,
            output_format=output_format
        )

        return {
            "success": True,
            "project_name": project_name,
            "synthesis": synthesis,
            "output_format": output_format,
            "metadata": {
                "documents_analyzed": len(documents),
                "timeline_entries": len(timeline) if timeline else 0,
                "related_projects": len(related_projects) if related_projects else 0,
                "word_count": len(synthesis.split()) if isinstance(synthesis, str) else 0
            }
        }

    async def _gather_project_documents(self, project_name: str) -> List[Dict[str, Any]]:
        """Gather all documents related to the project."""
        logger.info(f"Gathering documents for project: {project_name}")

        # Placeholder - would integrate with ObsidianRAG
        return [
            {
                "path": f"Projects/{project_name}/Overview.md",
                "title": f"{project_name} Overview",
                "content": "Project overview content...",
                "created": "2024-12-01",
                "modified": "2025-01-10"
            },
            {
                "path": f"Projects/{project_name}/Architecture.md",
                "title": "Architecture Design",
                "content": "Technical architecture details...",
                "created": "2024-12-05",
                "modified": "2025-01-08"
            },
            {
                "path": f"Projects/{project_name}/Roadmap.md",
                "title": "Project Roadmap",
                "content": "Phase 1, Phase 2, Phase 3...",
                "created": "2024-12-10",
                "modified": "2025-01-09"
            }
        ]

    async def _extract_project_metadata(self, documents: List[Dict]) -> Dict[str, Any]:
        """Extract structured metadata from project documents."""
        logger.info("Extracting project metadata")

        # Placeholder - would use NLP to extract
        return {
            "status": "In Progress",
            "phase": "Phase 3",
            "owner": "John Doe",
            "team_size": 5,
            "start_date": "2024-12-01",
            "target_completion": "2025-03-01",
            "priority": "High",
            "tags": ["#ai", "#automation", "#assistant"]
        }

    async def _generate_timeline(self, documents: List[Dict]) -> List[Dict[str, Any]]:
        """Generate chronological timeline from documents."""
        logger.info("Generating project timeline")

        # Placeholder - would extract dates and events
        return [
            {
                "date": "2024-12-01",
                "event": "Project kickoff",
                "source": "Overview.md"
            },
            {
                "date": "2024-12-15",
                "event": "Completed Phase 1: Local RAG",
                "source": "Roadmap.md"
            },
            {
                "date": "2025-01-05",
                "event": "Started Phase 3: Orchestration",
                "source": "Roadmap.md"
            }
        ]

    async def _find_related_projects(
        self,
        project_name: str,
        documents: List[Dict]
    ) -> List[Dict[str, str]]:
        """Find related projects based on links and content."""
        logger.info("Finding related projects")

        # Placeholder - would analyze links and semantic similarity
        return [
            {
                "name": "Knowledge_Management",
                "relationship": "Dependency",
                "description": "Provides core knowledge storage"
            },
            {
                "name": "Automation_Framework",
                "relationship": "Integration",
                "description": "Shared automation capabilities"
            }
        ]

    def _synthesize_output(
        self,
        project_name: str,
        metadata: Dict,
        documents: List[Dict],
        timeline: Optional[List[Dict]],
        related_projects: Optional[List[Dict]],
        output_format: str
    ) -> str:
        """Synthesize all data into requested format."""
        if output_format == "markdown":
            output = f"""# {project_name} - Project Synthesis

## Overview

**Status**: {metadata['status']}
**Phase**: {metadata['phase']}
**Owner**: {metadata['owner']}
**Team Size**: {metadata['team_size']} people
**Started**: {metadata['start_date']}
**Target Completion**: {metadata['target_completion']}
**Priority**: {metadata['priority']}

## Documents

{len(documents)} documents analyzed:

"""
            for doc in documents:
                output += f"- **{doc['title']}** ({doc['path']})\n"
                output += f"  Last updated: {doc['modified']}\n\n"

            if timeline:
                output += "\n## Timeline\n\n"
                for event in timeline:
                    output += f"- **{event['date']}**: {event['event']}\n"

            if related_projects:
                output += "\n## Related Projects\n\n"
                for proj in related_projects:
                    output += f"### {proj['name']}\n"
                    output += f"- **Relationship**: {proj['relationship']}\n"
                    output += f"- {proj['description']}\n\n"

            return output

        elif output_format == "executive_summary":
            return f"""PROJECT SUMMARY: {project_name}

Status: {metadata['status']} | Phase: {metadata['phase']} | Priority: {metadata['priority']}

Currently analyzing {len(documents)} project documents. Project started {metadata['start_date']}
with target completion {metadata['target_completion']}. Team of {metadata['team_size']} led by {metadata['owner']}.

Key milestones: {len(timeline) if timeline else 0} events tracked.
Dependencies: {len(related_projects) if related_projects else 0} related projects identified.
"""

        elif output_format == "json":
            import json
            return json.dumps({
                "project_name": project_name,
                "metadata": metadata,
                "documents": documents,
                "timeline": timeline,
                "related_projects": related_projects
            }, indent=2)

        else:
            return f"Project synthesis for {project_name} in {output_format} format"
