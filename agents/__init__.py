"""
AI Executive Assistant - Agents Module
======================================

This module contains specialized agents for the AI Executive Assistant system.

Current Agents:
- local_rag: Privacy-first RAG agent for local document processing (Phase 1 ✅)
- cloud_integration: Path mapping service for hybrid local/cloud workflows (Phase 2 ✅)
- orchestrator: Multi-agent coordination and task routing (Phase 3 ✅)
- abstraction_layer: LLM-agnostic skill interface with adapters (Phase 4 ✅)

Future Enhancements:
- Real LLM API integrations (Claude, OpenAI, Gemini)
- Additional skills (email, file operations, web search)
- Skill composition and chaining
- Visual skill builder UI
"""

__version__ = "0.4.0"
__author__ = "AI Executive Assistant Team"

# Import main agent classes for convenience
try:
    from .local_rag.local_rag_agent import LocalRAGAgent, MockObsidianVault
    from .cloud_integration.path_mapping_service import PathMappingService
    from .orchestrator.supervisor_agent import create_supervisor_graph, run_query
    from .abstraction_layer.skill_abstraction_layer import (
        SkillRegistry,
        BaseSkill,
        ClaudeAdapter,
        OpenAIAdapter,
        GeminiAdapter
    )
    __all__ = [
        'LocalRAGAgent',
        'MockObsidianVault',
        'PathMappingService',
        'create_supervisor_graph',
        'run_query',
        'SkillRegistry',
        'BaseSkill',
        'ClaudeAdapter',
        'OpenAIAdapter',
        'GeminiAdapter'
    ]
except ImportError:
    # Dependencies not installed yet
    __all__ = []
