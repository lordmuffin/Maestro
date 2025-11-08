"""
Abstraction Layer Module - Phase 4
===================================

This module implements the Skill Abstraction Layer using the Adapter Pattern
to provide LLM-agnostic skill definitions.

Components:
----------
- BaseSkill: Abstract base class for all skills
- Pydantic schemas: Type-safe input definitions
- LLM Adapters: Provider-specific converters (Claude, OpenAI, Gemini)
- SkillRegistry: Central management and discovery

Key Features:
------------
- No vendor lock-in: Switch LLM providers easily
- Single source of truth: Define skills once
- Multi-LLM support: Use multiple providers simultaneously
- Type safety: Pydantic validation at runtime
- Auto-documentation: Schemas self-document

Included Skills:
---------------
- GenerateProjectSynthesis: Create project overviews
- ScheduleCalendarEvent: Google Calendar integration
- UpdateSpreadsheet: Google Sheets updates
- SearchKnowledgeBase: Vault semantic search

Usage:
-----
    from agents.abstraction_layer import SkillRegistry, GenerateProjectSynthesis

    # Register skills
    registry = SkillRegistry()
    registry.register_skill(GenerateProjectSynthesis())

    # Get provider-specific tools
    claude_tools = registry.get_tools_for_llm("claude")
    openai_tools = registry.get_tools_for_llm("openai")
    gemini_tools = registry.get_tools_for_llm("gemini")

    # Execute skill
    result = registry.execute_skill(
        "generate_project_synthesis",
        project_name="AI_Assistant",
        output_format="markdown"
    )

Adapters:
--------
Each adapter converts abstract skills to provider-specific formats:
- ClaudeAdapter: Anthropic tool schema
- OpenAIAdapter: OpenAI function schema
- GeminiAdapter: Google function declaration schema

Architecture Context:
--------------------
Phase 4 provides the Abstraction Plane that:
1. Defines skills in universal format
2. Adapts to any LLM provider
3. Enables vendor-independent development
4. Supports multi-LLM strategies

This completes the four-phase architecture:
- Phase 1: Local RAG (Privacy layer)
- Phase 2: Path Mapping (Cloud bridge)
- Phase 3: Orchestrator (Intelligence plane)
- Phase 4: Abstraction Layer (LLM interface) ✅
"""

__version__ = "4.0.0"
__phase__ = "Phase 4: Skill Abstraction Layer"
__status__ = "Abstraction Core Complete ✅"

try:
    from .skill_abstraction_layer import (
        # Base classes
        BaseSkill,
        BaseLLMAdapter,

        # Input schemas
        ProjectSynthesisInput,
        CalendarScheduleInput,
        SpreadsheetUpdateInput,
        KnowledgeSearchInput,

        # Skills
        GenerateProjectSynthesis,
        ScheduleCalendarEvent,
        UpdateSpreadsheet,
        SearchKnowledgeBase,

        # Adapters
        ClaudeAdapter,
        OpenAIAdapter,
        GeminiAdapter,

        # Registry
        SkillRegistry
    )

    __all__ = [
        # Base
        'BaseSkill',
        'BaseLLMAdapter',

        # Schemas
        'ProjectSynthesisInput',
        'CalendarScheduleInput',
        'SpreadsheetUpdateInput',
        'KnowledgeSearchInput',

        # Skills
        'GenerateProjectSynthesis',
        'ScheduleCalendarEvent',
        'UpdateSpreadsheet',
        'SearchKnowledgeBase',

        # Adapters
        'ClaudeAdapter',
        'OpenAIAdapter',
        'GeminiAdapter',

        # Registry
        'SkillRegistry'
    ]
except ImportError:
    # Dependencies not installed yet
    __all__ = []
