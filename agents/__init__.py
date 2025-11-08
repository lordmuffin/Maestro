"""
AI Executive Assistant - Agents Module
======================================

This module contains specialized agents for the AI Executive Assistant system.

Current Agents:
- local_rag: Privacy-first RAG agent for local document processing (Phase 1 ✅)
- cloud_integration: Path mapping service for hybrid local/cloud workflows (Phase 2 ✅)

Future Agents:
- orchestrator: Multi-agent coordination and task routing (Phase 2 - In Progress)
- cloud_agent: Cloud-based agent for complex reasoning tasks (Phase 3)
- tool_agent: Specialized agents for specific tools (calendar, email, etc.) (Phase 3-4)
"""

__version__ = "0.2.0"
__author__ = "AI Executive Assistant Team"

# Import main agent classes for convenience
try:
    from .local_rag.local_rag_agent import LocalRAGAgent, MockObsidianVault
    from .cloud_integration.path_mapping_service import PathMappingService
    __all__ = ['LocalRAGAgent', 'MockObsidianVault', 'PathMappingService']
except ImportError:
    # Dependencies not installed yet
    __all__ = []
