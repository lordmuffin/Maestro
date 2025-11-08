"""
AI Executive Assistant - Agents Module
======================================

This module contains specialized agents for the AI Executive Assistant system.

Current Agents:
- local_rag: Privacy-first RAG agent for local document processing

Future Agents:
- cloud_agent: Cloud-based agent for complex reasoning tasks
- orchestrator: Multi-agent coordination and task routing
- tool_agent: Specialized agents for specific tools (calendar, email, etc.)
"""

__version__ = "0.1.0"
__author__ = "AI Executive Assistant Team"

# Import main agent classes for convenience
try:
    from .local_rag.local_rag_agent import LocalRAGAgent, MockObsidianVault
    __all__ = ['LocalRAGAgent', 'MockObsidianVault']
except ImportError:
    # Dependencies not installed yet
    __all__ = []
