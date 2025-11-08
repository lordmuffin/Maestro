# Supervisor Agent - Phase 3: Multi-LLM Orchestration

## Overview

The Supervisor Agent implements the **Intelligence Plane** of the AI Executive Assistant, providing dynamic task routing across multiple specialized LLM agents. Using LangGraph, it orchestrates workflows based on data sensitivity and task type.

## Problem Statement

Different tasks require different capabilities:
- **Privacy-sensitive queries** need local processing
- **Complex synthesis** benefits from long-context models (Claude)
- **Automation tasks** require G-Suite integration (Gemini)

A static single-agent approach can't optimize for all these constraints simultaneously.

## Solution: Dynamic Multi-Agent Orchestration

The Supervisor Agent uses a **Routing Matrix** to intelligently distribute work:

### Routing Matrix

| Data Sensitivity | Task Type  | Agent Selected        | Rationale                    |
|-----------------|------------|-----------------------|------------------------------|
| **HIGH**        | Any        | Local RAG            | Privacy-first mandate        |
| **MEDIUM**      | Synthesis  | Claude               | 200K context window          |
| **MEDIUM**      | Automation | Gemini               | G-Suite API integration      |
| **LOW**         | Retrieval  | Local RAG            | Efficient, no cost           |
| **LOW**         | Synthesis  | Claude               | Superior reasoning           |
| **LOW**         | Automation | Gemini               | Workspace integration        |
| **Default**     | Unknown    | Local RAG            | Safe fallback                |

## Architecture

### LangGraph Workflow

```
                    START
                      │
                      ▼
              ┌──────────────┐
              │  CLASSIFIER  │
              │   (analyze   │
              │    query)    │
              └──────┬───────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ LOCAL  │  │ CLAUDE │  │ GEMINI │
    │  RAG   │  │ SYNTH  │  │ AUTO   │
    └───┬────┘  └───┬────┘  └───┬────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
                   END
```

### Components

#### 1. AgentState
TypedDict schema tracking workflow state:
```python
{
    "query": str,              # Original user query
    "classification": str,     # Routing decision
    "sensitivity": str,        # HIGH/MEDIUM/LOW
    "task_type": str,          # RETRIEVAL/SYNTHESIS/AUTOMATION
    "response": str,           # Final answer
    "agent_used": str,         # Which agent processed it
    "metadata": dict           # Additional context
}
```

#### 2. Classifier Node
Analyzes queries to determine routing:
- Detects privacy keywords → HIGH sensitivity
- Identifies synthesis needs → SYNTHESIS task
- Recognizes automation requests → AUTOMATION task
- Applies routing matrix logic

Current implementation: Rule-based keyword matching
Future: LLM-based classification for nuanced understanding

#### 3. Worker Nodes

**Local RAG Agent:**
- **Use case:** Privacy-sensitive retrieval
- **Integration:** Phase 1 LocalRAGAgent
- **Processing:** Fully local, zero external calls
- **Response time:** <1 second

**Claude Synthesis Agent:**
- **Use case:** Complex long-form analysis
- **Integration:** Phase 2 PathMappingService + Claude API
- **Context:** 200K token window
- **Response time:** 2-5 seconds

**Gemini Automation Agent:**
- **Use case:** G-Suite workflow automation
- **Integration:** Google Workspace APIs
- **Capabilities:** Sheets, Docs, Calendar, Gmail
- **Response time:** 1-3 seconds

## Installation

### Prerequisites
- Python 3.11+
- Phase 1 (Local RAG) and Phase 2 (Path Mapping) installed

### Setup

```bash
cd agents/orchestrator
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the demonstration:
```bash
python supervisor_agent.py
```

This executes 4 test cases demonstrating routing to all agents.

### Integration Example

```python
from agents.orchestrator.supervisor_agent import create_supervisor_graph

# Initialize orchestrator
graph = create_supervisor_graph()

# Execute query
result = graph.invoke({
    "query": "Analyze the themes in my private project notes",
    "classification": None,
    "sensitivity": None,
    "task_type": None,
    "response": None,
    "agent_used": None,
    "metadata": None
})

print(f"Agent used: {result['agent_used']}")
print(f"Response: {result['response']}")
```

### Connecting Real Agents

#### Local RAG Integration
```python
from agents.local_rag import LocalRAGAgent

def local_worker(state: AgentState) -> dict:
    agent = LocalRAGAgent(vault_path)
    agent.ingest_documents()
    agent.build_index()
    result = agent.query(state['query'])

    return {
        "response": result['response'],
        "agent_used": "local_rag",
        "metadata": {
            "chunks_retrieved": result['num_chunks_retrieved']
        }
    }
```

#### Claude Integration
```python
from agents.cloud_integration import PathMappingService
from anthropic import Anthropic

def claude_worker(state: AgentState) -> dict:
    # Get relevant file IDs
    mapping_service = PathMappingService()
    local_paths = get_relevant_paths(state['query'])
    gdrive_ids = [
        mapping_service.resolve_to_gdrive_id(p)
        for p in local_paths
    ]

    # Call Claude with file references
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{
            "role": "user",
            "content": state['query']
        }],
        # Would include file context here
    )

    return {
        "response": response.content[0].text,
        "agent_used": "claude_synthesis",
        "metadata": {"files_used": gdrive_ids}
    }
```

## Test Cases

The demo includes 4 test cases:

### Test 1: Privacy-Sensitive Query
```
Query: "What are the key points in my private meeting notes?"
Expected: → Local RAG Agent
Reason: HIGH sensitivity (keyword: "private")
```

### Test 2: Synthesis Query
```
Query: "Synthesize themes across all project documentation"
Expected: → Claude Agent
Reason: SYNTHESIS task (keyword: "synthesize")
```

### Test 3: Automation Query
```
Query: "Update sheet Q4_Planning with latest budget numbers"
Expected: → Gemini Agent
Reason: AUTOMATION task (keyword: "update sheet")
```

### Test 4: Default Fallback
```
Query: "What did I write about machine learning?"
Expected: → Local RAG Agent
Reason: No specific indicators, privacy-first default
```

## Routing Logic Details

### Classifier Implementation

Current: **Rule-based keyword matching**
- Fast, predictable, transparent
- No external API calls
- Easy to debug and extend

Keywords by category:
```python
PRIVACY_KEYWORDS = [
    'private', 'confidential', 'secret',
    'personal', 'sensitive'
]

SYNTHESIS_KEYWORDS = [
    'synthesize', 'analyze', 'compare',
    'summarize', 'research', 'explain',
    'comprehensive', 'deep dive'
]

AUTOMATION_KEYWORDS = [
    'update sheet', 'spreadsheet', 'calendar',
    'schedule', 'email', 'automate',
    'create doc', 'send to'
]
```

Future: **LLM-based classification**
- More nuanced understanding
- Handles edge cases better
- Requires API call overhead

### Decision Priority

1. **Sensitivity first:** HIGH sensitivity always → Local
2. **Task type second:** Determines cloud agent selection
3. **Default fallback:** When uncertain → Local (privacy-first)

## Performance

### Metrics

- **Routing overhead:** <50ms (classifier execution)
- **Total latency:** Depends on selected agent
  - Local: <1s
  - Claude: 2-5s
  - Gemini: 1-3s

### Scalability

- **Concurrent queries:** Limited by worker agents, not orchestrator
- **State size:** Minimal (~1KB per query)
- **Memory usage:** ~10MB for orchestrator process

## Configuration

### Environment Variables

```bash
# Optional: For real LLM integration
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/creds.json"

# Vault location (for Local RAG)
export OBSIDIAN_VAULT_PATH="/path/to/vault"
```

### Customization

#### Adding New Agents

```python
# 1. Define worker function
def new_agent_worker(state: AgentState) -> dict:
    # Implementation
    return {"response": "...", "agent_used": "new_agent"}

# 2. Update classifier
def classify_query(state: AgentState) -> dict:
    # Add new routing logic
    if some_condition:
        return {"classification": "new_agent"}

# 3. Add to graph
workflow.add_node("new_agent", new_agent_worker)
workflow.add_conditional_edges(
    "classifier",
    lambda state: state["classification"],
    {"new_agent": "new_agent", ...}
)
```

#### Modifying Routing Matrix

Edit `classify_query()` function:
```python
# Example: Add urgency-based routing
if 'urgent' in query:
    return {
        "classification": "claude",  # Faster cloud processing
        "sensitivity": "MEDIUM",
        "task_type": "SYNTHESIS"
    }
```

## Integration Points

### Phase 1: Local RAG Agent
- **Status:** Ready for integration
- **Interface:** LocalRAGAgent.query(text)
- **Returns:** Dict with response and context

### Phase 2: Path Mapping Service
- **Status:** Ready for integration
- **Interface:** PathMappingService.resolve_to_gdrive_id(path)
- **Returns:** Google Drive File ID

### Phase 3: Supervisor (This)
- **Status:** Complete (demo mode)
- **Next:** Connect to real agents from Phase 1 & 2

## Limitations & Future Work

### Current Limitations

1. **Rule-based classifier:** Simple keyword matching
   - Can't handle complex or ambiguous queries
   - No learning from past decisions

2. **No conversation memory:** Each query is independent
   - Can't maintain context across multiple turns
   - No personalization based on history

3. **Static routing:** Routing matrix is hardcoded
   - Can't adapt to changing conditions
   - No load balancing or failover

4. **Simulated workers:** Demo uses mock responses
   - Need real API integrations
   - Error handling not comprehensive

### Roadmap

#### Short-term
- [ ] Integrate real LocalRAGAgent from Phase 1
- [ ] Connect PathMappingService for cloud workers
- [ ] Add Claude API integration with file context
- [ ] Add Gemini API integration for G-Suite

#### Medium-term
- [ ] LLM-based classifier for better routing
- [ ] Conversation memory and multi-turn context
- [ ] Cost tracking and optimization
- [ ] Performance monitoring dashboard

#### Long-term
- [ ] Self-learning routing (ML-based optimization)
- [ ] Dynamic agent registry (plugin system)
- [ ] Multi-agent collaboration (agents consulting each other)
- [ ] Streaming responses for better UX

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'langgraph'`

**Solution:**
```bash
pip install langgraph langchain-core
```

### Routing Issues

**Problem:** Query routed to wrong agent

**Solution:**
1. Check keyword matching in `classify_query()`
2. Review routing matrix logic
3. Add logging to see classification decision:
```python
print(f"Query: {query}")
print(f"Matched keywords: {matched}")
print(f"Classification: {classification}")
```

### Integration Failures

**Problem:** Worker functions fail

**Solution:**
1. Verify Phase 1 and Phase 2 modules are installed
2. Check environment variables are set
3. Test workers independently before orchestration

## API Reference

### create_supervisor_graph()
Create the LangGraph workflow.

**Returns:** Compiled StateGraph

### run_query(graph, query)
Execute a query through the orchestration workflow.

**Parameters:**
- `graph`: Compiled LangGraph
- `query`: User query string

**Returns:** Final AgentState dict

### classify_query(state)
Classifier node - routes based on routing matrix.

**Parameters:**
- `state`: Current AgentState

**Returns:** Updated state with classification

### local_worker(state)
Local RAG agent worker.

**Parameters:**
- `state`: Current AgentState

**Returns:** Updated state with response

### claude_worker(state)
Claude synthesis agent worker.

**Parameters:**
- `state`: Current AgentState

**Returns:** Updated state with response

### gemini_worker(state)
Gemini automation agent worker.

**Parameters:**
- `state`: Current AgentState

**Returns:** Updated state with response

## Testing

Run the full demonstration:
```bash
python supervisor_agent.py
```

Expected output:
- 4 test queries execute successfully
- Each routes to appropriate agent
- Responses generated for all cases
- Summary shows routing validation

## Contributing

Phase 3 is complete but can be extended:

1. **Better classification:** Implement LLM-based classifier
2. **More agents:** Add specialized workers
3. **Conversation memory:** Add context tracking
4. **Monitoring:** Add telemetry and dashboards

## References

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Google AI Studio](https://ai.google.dev/)

## License

[Specify License]

---

**Status**: Phase 3 Complete ✅ - Orchestration Core
**Next**: Integrate real agents from Phase 1 & 2
**Last Updated**: 2025-11-08
