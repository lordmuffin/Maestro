"""
Orchestrator Module - Phase 3
==============================

This module implements multi-agent orchestration using LangGraph for the
AI Executive Assistant system.

Components:
----------
- SupervisorAgent: Central control flow with routing matrix
- AgentState: TypedDict schema for workflow state
- Worker nodes: local_worker, claude_worker, gemini_worker
- Classifier node: Query analysis and routing logic

Key Features:
------------
- Dynamic task routing based on sensitivity and task type
- LangGraph StateGraph for workflow orchestration
- Conditional edges for intelligent agent selection
- Integration with Phase 1 (Local RAG) and Phase 2 (Path Mapping)

Routing Matrix:
--------------
| Sensitivity | Task Type  | Agent          |
|-------------|------------|----------------|
| HIGH        | Any        | Local RAG      |
| MEDIUM      | Synthesis  | Claude         |
| MEDIUM      | Automation | Gemini         |
| LOW         | Any        | Based on task  |

Usage:
-----
    from agents.orchestrator import create_supervisor_graph, run_query

    # Create orchestrator
    graph = create_supervisor_graph()

    # Execute query
    result = graph.invoke({
        "query": "What are my private notes about X?",
        "classification": None,
        "sensitivity": None,
        "task_type": None,
        "response": None,
        "agent_used": None,
        "metadata": None
    })

    print(f"Agent: {result['agent_used']}")
    print(f"Response: {result['response']}")

Architecture Context:
--------------------
Phase 3 provides the Intelligence Plane that:
1. Analyzes incoming queries
2. Determines optimal agent for task
3. Routes to appropriate worker
4. Collects and returns results

This enables the Tri-Hybrid architecture:
- Local processing for privacy
- Cloud agents for complex tasks
- Intelligent routing between them
"""

__version__ = "3.0.0"
__phase__ = "Phase 3: Multi-LLM Orchestration"
__status__ = "Orchestration Core Complete ✅"

try:
    from .supervisor_agent import (
        AgentState,
        create_supervisor_graph,
        run_query,
        classify_query,
        local_worker,
        claude_worker,
        gemini_worker
    )

    __all__ = [
        'AgentState',
        'create_supervisor_graph',
        'run_query',
        'classify_query',
        'local_worker',
        'claude_worker',
        'gemini_worker'
    ]
except ImportError:
    # Dependencies not installed yet
    __all__ = []
