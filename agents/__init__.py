"""
AI Executive Assistant - Agents Module
======================================

This module contains specialized agents for the AI Executive Assistant system.

Current Agents:
- local_rag: Privacy-first RAG agent for local document processing (Phase 1 ✅)
- cloud_integration: Path mapping service for hybrid local/cloud workflows (Phase 2 ✅)
- orchestrator: Multi-agent coordination and task routing (Phase 3 ✅)

Future Agents:
- cloud_agent: Real Claude/Gemini API integrations (Phase 3 - Next)
- tool_agent: Specialized agents for specific tools (calendar, email, etc.) (Phase 3-4)
"""

__version__ = "0.3.0"
__author__ = "AI Executive Assistant Team"

# Import main agent classes for convenience
try:
    from .local_rag.local_rag_agent import LocalRAGAgent, MockObsidianVault
    from .cloud_integration.path_mapping_service import PathMappingService
    from .orchestrator.supervisor_agent import create_supervisor_graph, run_query
    __all__ = [
        'LocalRAGAgent',
        'MockObsidianVault',
        'PathMappingService',
        'create_supervisor_graph',
        'run_query'
    ]
except ImportError:
    # Dependencies not installed yet
    __all__ = []
