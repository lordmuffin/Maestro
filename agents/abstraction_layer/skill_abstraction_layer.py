#!/usr/bin/env python3
"""
Skill Abstraction Layer - Phase 4: Unified LLM Interface
=========================================================

This module implements the Abstraction Plane for the AI Executive Assistant,
providing LLM-agnostic skill definitions and vendor-specific adapters.

Problem Statement:
-----------------
LLM providers use different tool/function calling schemas:
- Anthropic Claude: "tools" with specific input_schema format
- OpenAI GPT: "functions" with different JSON schema structure
- Google Gemini: "function_declarations" with yet another format

Hardcoding to one provider creates vendor lock-in and makes it difficult
to switch providers or use multiple LLMs simultaneously.

Solution: Adapter Pattern
-------------------------
1. Define skills once using a universal format (Pydantic models)
2. Create adapters that convert to provider-specific schemas
3. Maintain single source of truth for skill definitions
4. Enable easy addition of new LLM providers

Architecture:
------------
    ┌──────────────────────────────┐
    │   Abstract Skill Definition   │
    │   (Pydantic BaseModel)        │
    └────────────┬─────────────────┘
                 │
         ┌───────┴────────┐
         │   ADAPTERS     │
         ├────────────────┤
         │  Claude        │
         │  OpenAI        │
         │  Gemini        │
         │  Custom...     │
         └───────┬────────┘
                 │
         ┌───────┴────────┐
         │  LLM Provider  │
         │  Tool Calling  │
         └────────────────┘

Benefits:
--------
✓ No vendor lock-in
✓ Single skill definition
✓ Easy provider switching
✓ Multi-LLM support
✓ Maintainable codebase

Author: AI Executive Assistant Team
Version: 4.0.0
Status: Phase 4 - Skill Abstraction
"""

from typing import Any, Dict, List, Optional, Type, get_type_hints, get_origin, get_args
from pydantic import BaseModel, Field
from enum import Enum
import json
from abc import ABC, abstractmethod


# ============================================================================
# Abstract Skill Definitions (Universal Format)
# ============================================================================

class ProjectSynthesisInput(BaseModel):
    """
    Input schema for Project Synthesis skill.

    This Pydantic model serves dual purposes:
    1. Runtime validation of skill inputs
    2. Schema generation for LLM tool calling

    Field descriptions are CRITICAL for LLM tool use - they guide the LLM
    in understanding when and how to use the skill.
    """
    project_name: str = Field(
        ...,
        description=(
            "The name of the project to synthesize. Should match a project "
            "folder or tag in your Obsidian vault (e.g., 'Project_Nexus', "
            "'AI_Assistant'). Case-sensitive."
        ),
        examples=["Project_Nexus", "Q4_Planning", "AI_Assistant"]
    )

    output_format: str = Field(
        default="markdown",
        description=(
            "The desired output format for the synthesis. Options: "
            "'markdown' (default, for documents), 'json' (for structured data), "
            "'html' (for web display), 'pdf' (for formal reports)."
        ),
        examples=["markdown", "json", "html", "pdf"]
    )


class CalendarScheduleInput(BaseModel):
    """Input schema for Calendar Scheduling skill."""

    event_title: str = Field(
        ...,
        description="Title of the calendar event (e.g., 'Team Standup', 'Client Meeting')",
        examples=["Team Standup", "Quarterly Review", "1:1 with Manager"]
    )

    datetime_str: str = Field(
        ...,
        description=(
            "Event date and time in ISO format (YYYY-MM-DDTHH:MM:SS) or "
            "natural language (e.g., 'tomorrow at 2pm', 'next Monday 10am')"
        ),
        examples=["2025-11-15T14:00:00", "tomorrow at 2pm", "next Friday 10am"]
    )

    duration_minutes: int = Field(
        default=60,
        description="Duration of the event in minutes",
        ge=15,  # Minimum 15 minutes
        le=480,  # Maximum 8 hours
        examples=[30, 60, 90]
    )

    attendees: List[str] = Field(
        default_factory=list,
        description="List of attendee email addresses",
        examples=[["john@company.com", "jane@company.com"], []]
    )


class SpreadsheetUpdateInput(BaseModel):
    """Input schema for Spreadsheet Update skill."""

    spreadsheet_name: str = Field(
        ...,
        description="Name or ID of the Google Sheets spreadsheet to update",
        examples=["Q4_Budget", "Team_Metrics", "Project_Timeline"]
    )

    range_notation: str = Field(
        ...,
        description=(
            "Cell range in A1 notation (e.g., 'A1:B10', 'Sheet2!C5:E20'). "
            "Specifies which cells to update."
        ),
        examples=["A1:B10", "Sheet2!C5:E20", "Budget!A1"]
    )

    values: List[List[Any]] = Field(
        ...,
        description=(
            "2D array of values to write. Each inner list represents a row. "
            "Example: [['Header1', 'Header2'], ['Value1', 'Value2']]"
        ),
        examples=[[["Name", "Score"], ["Alice", "95"], ["Bob", "87"]]]
    )

    value_input_option: str = Field(
        default="USER_ENTERED",
        description=(
            "How values should be interpreted: 'USER_ENTERED' (formulas evaluated) "
            "or 'RAW' (stored as-is)"
        ),
        examples=["USER_ENTERED", "RAW"]
    )


class SearchFormat(str, Enum):
    """Enum for search result formats."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    RAW = "raw"


class KnowledgeSearchInput(BaseModel):
    """Input schema for Knowledge Base Search skill."""

    query: str = Field(
        ...,
        description="Natural language search query for the knowledge base",
        examples=["recent meeting notes about AI project", "budget information for Q4"]
    )

    search_scope: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of folders or tags to limit search scope. "
            "If None, searches entire vault."
        ),
        examples=[["Projects/AI_Assistant", "Meetings"], ["#important", "#project"]]
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


# ============================================================================
# Abstract Skill Class
# ============================================================================

class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    Defines the contract that all skills must follow, regardless of
    which LLM provider they're used with.
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel]
    ):
        """
        Initialize a skill.

        Args:
            name: Unique identifier for the skill (used in tool calling)
            description: Clear explanation of what the skill does (for LLM)
            input_schema: Pydantic model defining expected inputs
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the skill with provided inputs.

        Args:
            **kwargs: Inputs matching the input_schema

        Returns:
            Dict containing execution results
        """
        pass

    def validate_input(self, **kwargs) -> BaseModel:
        """
        Validate inputs against the schema.

        Args:
            **kwargs: Raw input data

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If inputs don't match schema
        """
        return self.input_schema(**kwargs)

    def __repr__(self) -> str:
        return f"<Skill: {self.name}>"


# ============================================================================
# Concrete Skill Implementations
# ============================================================================

class GenerateProjectSynthesis(BaseSkill):
    """
    Skill for generating comprehensive project syntheses from vault documents.

    This skill combines:
    - Phase 1: Local RAG for document retrieval
    - Phase 2: Path Mapping for cloud file access
    - Phase 3: Orchestrator for routing to appropriate LLM
    """

    def __init__(self):
        super().__init__(
            name="generate_project_synthesis",
            description=(
                "Generate a comprehensive synthesis of all notes, documents, and "
                "information related to a specific project in your Obsidian vault. "
                "Useful for creating project overviews, status reports, or "
                "understanding project evolution over time."
            ),
            input_schema=ProjectSynthesisInput
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute project synthesis."""
        inputs = self.validate_input(**kwargs)

        # Simulated execution (in production, would integrate with Phase 1-3)
        return {
            "status": "success",
            "project_name": inputs.project_name,
            "synthesis": f"[Comprehensive synthesis of {inputs.project_name} in {inputs.output_format} format]",
            "sources_used": ["file1.md", "file2.md", "file3.md"],
            "word_count": 1250,
            "output_format": inputs.output_format
        }


class ScheduleCalendarEvent(BaseSkill):
    """Skill for scheduling calendar events via G-Suite API."""

    def __init__(self):
        super().__init__(
            name="schedule_calendar_event",
            description=(
                "Schedule a new event on your Google Calendar. Can parse natural "
                "language dates/times and automatically invite attendees. Integrates "
                "with your work calendar."
            ),
            input_schema=CalendarScheduleInput
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute calendar scheduling."""
        inputs = self.validate_input(**kwargs)

        return {
            "status": "success",
            "event_id": "evt_abc123",
            "event_title": inputs.event_title,
            "scheduled_time": inputs.datetime_str,
            "duration_minutes": inputs.duration_minutes,
            "attendees_invited": len(inputs.attendees),
            "calendar_link": "https://calendar.google.com/event/evt_abc123"
        }


class UpdateSpreadsheet(BaseSkill):
    """Skill for updating Google Sheets spreadsheets."""

    def __init__(self):
        super().__init__(
            name="update_spreadsheet",
            description=(
                "Update cells in a Google Sheets spreadsheet with new values. "
                "Supports formulas, multiple rows/columns, and different value "
                "input modes. Useful for automating data entry and reporting."
            ),
            input_schema=SpreadsheetUpdateInput
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spreadsheet update."""
        inputs = self.validate_input(**kwargs)

        total_cells = sum(len(row) for row in inputs.values)

        return {
            "status": "success",
            "spreadsheet_name": inputs.spreadsheet_name,
            "range_updated": inputs.range_notation,
            "cells_updated": total_cells,
            "rows_affected": len(inputs.values),
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/{inputs.spreadsheet_name}"
        }


class SearchKnowledgeBase(BaseSkill):
    """Skill for searching the Obsidian knowledge base."""

    def __init__(self):
        super().__init__(
            name="search_knowledge_base",
            description=(
                "Search your Obsidian vault for relevant documents and notes. "
                "Uses semantic search (not just keyword matching) to find the "
                "most relevant information. Can be scoped to specific folders or tags."
            ),
            input_schema=KnowledgeSearchInput
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute knowledge base search."""
        inputs = self.validate_input(**kwargs)

        return {
            "status": "success",
            "query": inputs.query,
            "results_found": inputs.max_results,
            "search_scope": inputs.search_scope or ["entire_vault"],
            "result_format": inputs.result_format.value,
            "results": [
                {"file": "project_notes.md", "relevance": 0.95},
                {"file": "meeting_2025-11-08.md", "relevance": 0.87}
            ]
        }


# ============================================================================
# LLM Adapters
# ============================================================================

class BaseLLMAdapter(ABC):
    """Abstract base class for LLM-specific adapters."""

    @abstractmethod
    def adapt_skill_to_tool_schema(self, skill: BaseSkill) -> Dict[str, Any]:
        """Convert abstract skill to provider-specific tool schema."""
        pass

    @abstractmethod
    def parse_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Parse provider-specific tool call into standard format."""
        pass


class ClaudeAdapter(BaseLLMAdapter):
    """
    Adapter for Anthropic Claude tool calling format.

    Claude uses the following tool schema:
    {
        "name": "skill_name",
        "description": "What the skill does",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
    """

    def adapt_skill_to_tool_schema(self, skill: BaseSkill) -> Dict[str, Any]:
        """
        Convert abstract skill to Claude tool schema.

        Args:
            skill: BaseSkill instance to convert

        Returns:
            Dict in Claude's tool format

        Example output:
        {
            "name": "generate_project_synthesis",
            "description": "Generate comprehensive project synthesis...",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The name of the project..."
                    },
                    ...
                },
                "required": ["project_name"]
            }
        }
        """
        # Get JSON schema from Pydantic model
        pydantic_schema = skill.input_schema.model_json_schema()

        # Extract properties and required fields
        properties = pydantic_schema.get("properties", {})
        required = pydantic_schema.get("required", [])

        # Build Claude-specific tool schema
        claude_tool = {
            "name": skill.name,
            "description": skill.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

        return claude_tool

    def parse_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Claude tool call into standard format.

        Args:
            tool_call: Claude's tool call structure

        Returns:
            Standardized tool call dict
        """
        return {
            "tool_name": tool_call.get("name"),
            "tool_input": tool_call.get("input", {})
        }


class OpenAIAdapter(BaseLLMAdapter):
    """
    Adapter for OpenAI function calling format.

    OpenAI uses "functions" with a slightly different schema structure.
    """

    def adapt_skill_to_tool_schema(self, skill: BaseSkill) -> Dict[str, Any]:
        """Convert abstract skill to OpenAI function schema."""
        pydantic_schema = skill.input_schema.model_json_schema()

        openai_function = {
            "name": skill.name,
            "description": skill.description,
            "parameters": {
                "type": "object",
                "properties": pydantic_schema.get("properties", {}),
                "required": pydantic_schema.get("required", [])
            }
        }

        return openai_function

    def parse_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenAI function call into standard format."""
        return {
            "tool_name": tool_call.get("function", {}).get("name"),
            "tool_input": json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        }


class GeminiAdapter(BaseLLMAdapter):
    """
    Adapter for Google Gemini function calling format.

    Gemini uses "function_declarations" with yet another schema structure.
    """

    def adapt_skill_to_tool_schema(self, skill: BaseSkill) -> Dict[str, Any]:
        """Convert abstract skill to Gemini function declaration schema."""
        pydantic_schema = skill.input_schema.model_json_schema()

        # Gemini uses a slightly different type mapping
        properties = {}
        for prop_name, prop_schema in pydantic_schema.get("properties", {}).items():
            properties[prop_name] = {
                "type": self._map_type_to_gemini(prop_schema.get("type")),
                "description": prop_schema.get("description", "")
            }

        gemini_function = {
            "name": skill.name,
            "description": skill.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": pydantic_schema.get("required", [])
            }
        }

        return gemini_function

    def _map_type_to_gemini(self, json_type: str) -> str:
        """Map JSON Schema types to Gemini types."""
        type_map = {
            "string": "STRING",
            "integer": "INTEGER",
            "number": "NUMBER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT"
        }
        return type_map.get(json_type, "STRING")

    def parse_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gemini function call into standard format."""
        return {
            "tool_name": tool_call.get("name"),
            "tool_input": tool_call.get("args", {})
        }


# ============================================================================
# Skill Registry
# ============================================================================

class SkillRegistry:
    """
    Central registry for all available skills.

    Provides discovery, registration, and adapter management for skills.
    """

    def __init__(self):
        """Initialize the skill registry."""
        self.skills: Dict[str, BaseSkill] = {}
        self.adapters: Dict[str, BaseLLMAdapter] = {
            "claude": ClaudeAdapter(),
            "openai": OpenAIAdapter(),
            "gemini": GeminiAdapter()
        }

    def register_skill(self, skill: BaseSkill) -> None:
        """
        Register a new skill.

        Args:
            skill: BaseSkill instance to register
        """
        if skill.name in self.skills:
            print(f"⚠️  Warning: Overwriting existing skill '{skill.name}'")

        self.skills[skill.name] = skill
        print(f"✓ Registered skill: {skill.name}")

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[str]:
        """List all registered skill names."""
        return list(self.skills.keys())

    def get_tools_for_llm(self, llm_provider: str) -> List[Dict[str, Any]]:
        """
        Get all skills adapted for a specific LLM provider.

        Args:
            llm_provider: One of "claude", "openai", "gemini"

        Returns:
            List of provider-specific tool schemas
        """
        adapter = self.adapters.get(llm_provider.lower())
        if not adapter:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

        return [
            adapter.adapt_skill_to_tool_schema(skill)
            for skill in self.skills.values()
        ]

    def execute_skill(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of the skill to execute
            **kwargs: Skill inputs

        Returns:
            Execution results
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")

        return skill.execute(**kwargs)


# ============================================================================
# Demonstration and Testing
# ============================================================================

def demonstrate_skill_abstraction():
    """
    Comprehensive demonstration of the skill abstraction layer.

    Shows:
    1. Skill registration
    2. Adaptation to different LLM providers
    3. Schema comparison
    4. Execution workflow
    """
    print("=" * 80)
    print("SKILL ABSTRACTION LAYER - DEMONSTRATION")
    print("Phase 4: Unified LLM Interface")
    print("=" * 80)

    # Initialize registry and register skills
    print("\n[STEP 1] Registering Skills")
    print("-" * 80)

    registry = SkillRegistry()

    skills = [
        GenerateProjectSynthesis(),
        ScheduleCalendarEvent(),
        UpdateSpreadsheet(),
        SearchKnowledgeBase()
    ]

    for skill in skills:
        registry.register_skill(skill)

    print(f"\n✅ Registered {len(skills)} skills")
    print(f"   Available: {', '.join(registry.list_skills())}")

    # Demonstrate adaptation to Claude
    print("\n\n[STEP 2] Adapting Skills for Claude (Anthropic)")
    print("-" * 80)

    claude_tools = registry.get_tools_for_llm("claude")
    print(f"\n✓ Generated {len(claude_tools)} Claude tool schemas")

    # Show one example in detail
    print("\n📋 Example: Project Synthesis Tool (Claude format)")
    print(json.dumps(claude_tools[0], indent=2))

    # Demonstrate adaptation to OpenAI
    print("\n\n[STEP 3] Adapting Skills for OpenAI (GPT)")
    print("-" * 80)

    openai_tools = registry.get_tools_for_llm("openai")
    print(f"\n✓ Generated {len(openai_tools)} OpenAI function schemas")

    print("\n📋 Example: Project Synthesis Function (OpenAI format)")
    print(json.dumps(openai_tools[0], indent=2))

    # Demonstrate adaptation to Gemini
    print("\n\n[STEP 4] Adapting Skills for Gemini (Google)")
    print("-" * 80)

    gemini_tools = registry.get_tools_for_llm("gemini")
    print(f"\n✓ Generated {len(gemini_tools)} Gemini function schemas")

    print("\n📋 Example: Project Synthesis Function (Gemini format)")
    print(json.dumps(gemini_tools[0], indent=2))

    # Demonstrate skill execution
    print("\n\n[STEP 5] Executing Skills")
    print("-" * 80)

    print("\n🔧 Executing: generate_project_synthesis")
    result1 = registry.execute_skill(
        "generate_project_synthesis",
        project_name="AI_Assistant",
        output_format="markdown"
    )
    print(json.dumps(result1, indent=2))

    print("\n🔧 Executing: schedule_calendar_event")
    result2 = registry.execute_skill(
        "schedule_calendar_event",
        event_title="Team Standup",
        datetime_str="2025-11-15T10:00:00",
        duration_minutes=30,
        attendees=["alice@company.com", "bob@company.com"]
    )
    print(json.dumps(result2, indent=2))

    # Demonstrate validation
    print("\n\n[STEP 6] Input Validation")
    print("-" * 80)

    print("\n✓ Valid input (will succeed):")
    try:
        result = registry.execute_skill(
            "update_spreadsheet",
            spreadsheet_name="Q4_Budget",
            range_notation="A1:B2",
            values=[["Header1", "Header2"], ["Value1", "Value2"]]
        )
        print("   Success!")
    except Exception as e:
        print(f"   Failed: {e}")

    print("\n✗ Invalid input (will fail):")
    try:
        result = registry.execute_skill(
            "update_spreadsheet",
            spreadsheet_name="Q4_Budget",
            range_notation="A1:B2"
            # Missing required 'values' field
        )
        print("   Success!")
    except Exception as e:
        print(f"   Failed (as expected): {type(e).__name__}")

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n✅ Skills Abstraction Layer Complete")

    print("\n📊 Statistics:")
    print(f"   • Skills registered: {len(skills)}")
    print(f"   • LLM adapters: {len(registry.adapters)}")
    print(f"   • Total tool schemas generated: {len(claude_tools) + len(openai_tools) + len(gemini_tools)}")

    print("\n🎯 Benefits Demonstrated:")
    print("   ✓ Single skill definition")
    print("   ✓ Multi-provider adaptation")
    print("   ✓ Schema validation")
    print("   ✓ Execution workflow")
    print("   ✓ No vendor lock-in")

    print("\n🔗 Integration Points:")
    print("   • Phase 1: Skills execute via LocalRAGAgent")
    print("   • Phase 2: Skills use PathMappingService for cloud files")
    print("   • Phase 3: Orchestrator routes to appropriate skill")
    print("   • Phase 4: Abstraction layer (THIS) provides LLM adapters")

    print("\n📈 Next Steps:")
    print("   → Connect skills to real API implementations")
    print("   → Add more skills (email, file operations, etc.)")
    print("   → Implement skill composition (chaining skills)")
    print("   → Add skill versioning and deprecation")
    print("   → Build skill marketplace/registry")

    print("\n" + "=" * 80)
    print("Demonstration Complete! 🎉")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    demonstrate_skill_abstraction()


if __name__ == "__main__":
    main()
