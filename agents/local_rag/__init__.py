"""
Local RAG Agent - Phase 1
==========================

Privacy-first Retrieval-Augmented Generation system for the AI Executive Assistant.

This module provides:
- LocalRAGAgent: Main agent class for document ingestion and querying
- MockObsidianVault: Test utility for creating mock Obsidian vaults
- query_ollama_mock: Simulated LLM inference for testing

Key Features:
- Full local processing (no external API calls)
- Obsidian vault integration
- FAISS vector store for efficient retrieval
- LlamaIndex-based RAG pipeline

Usage:
    from agents.local_rag import LocalRAGAgent

    agent = LocalRAGAgent("/path/to/vault")
    agent.ingest_documents()
    agent.build_index()
    result = agent.query("What are my priorities?")
"""

__version__ = "1.0.0"
__phase__ = "Phase 1: Local-First Knowledge Core"
__status__ = "Complete"

from .local_rag_agent import (
    LocalRAGAgent,
    MockObsidianVault,
    query_ollama_mock
)

__all__ = [
    'LocalRAGAgent',
    'MockObsidianVault',
    'query_ollama_mock'
]
