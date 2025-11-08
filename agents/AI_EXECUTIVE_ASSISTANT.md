# AI Executive Assistant - Tri-Hybrid Architecture

## Project Overview

This is a comprehensive AI Executive Assistant system built on a "Tri-Hybrid" architecture that combines:

1. **Local-First RAG** (Privacy-preserving knowledge retrieval)
2. **Cloud-Based Agents** (Complex reasoning and task execution)
3. **Human-in-the-Loop** (Oversight and decision-making)

## Architecture Philosophy

### Core Principles

- **Privacy First**: Sensitive data stays local by default
- **Progressive Enhancement**: Start simple, add complexity as needed
- **User Control**: Explicit consent for data sharing and cloud operations
- **Transparency**: Clear visibility into what the system is doing
- **Modularity**: Independent agents that can be composed flexibly

### Design Rationale

The Tri-Hybrid approach addresses three key challenges:

1. **Privacy vs. Capability Trade-off**
   - Local RAG handles most queries with full privacy
   - Cloud agents used only when local processing is insufficient
   - User explicitly approves cloud operations

2. **Performance vs. Cost**
   - Local processing is free and fast for routine tasks
   - Cloud resources used selectively for complex reasoning
   - Efficient routing minimizes cloud API costs

3. **Autonomy vs. Control**
   - Agents can operate autonomously within defined boundaries
   - Human oversight for critical decisions
   - Transparent decision-making process

## Four-Phase Development Plan

### Phase 1: Local-First Knowledge Core ✅ COMPLETE

**Goal**: Build privacy-preserving RAG subsystem

**Components**:
- ✅ Mock Obsidian vault creation
- ✅ LlamaIndex document ingestion
- ✅ FAISS vector store
- ✅ Basic RAG query pipeline
- ✅ Mock Ollama LLM integration

**Status**: Implemented in `/agents/local_rag/`

**Key Files**:
- `local_rag_agent.py`: Main RAG agent implementation
- `requirements.txt`: Dependencies for local RAG
- `README.md`: Detailed documentation

### Phase 2: Cloud Knowledge Integration 🔄 IN PROGRESS

**Goal**: Bridge local and cloud file references for hybrid RAG workflows

**Completed Components**:
- ✅ PathMappingService: Bidirectional local ↔ cloud path translation
- ✅ Path mangling logic (hierarchical → flat)
- ✅ O(1) lookup performance with triple-index architecture
- ✅ Bulk registration for efficient vault sync
- ✅ JSON import/export for persistence
- ✅ Statistics and monitoring

**Status**: Path mapping core complete, implemented in `/agents/cloud_integration/`

**Key Files**:
- `path_mapping_service.py`: Main path mapping service (600+ lines)
- `requirements.txt`: Dependencies (none - pure Python)
- `README.md`: Comprehensive documentation

**Planned Components** (Next in Phase 2):
- [ ] Master orchestrator agent
- [ ] Task decomposition system
- [ ] Agent registry and capabilities
- [ ] Inter-agent communication protocol
- [ ] Agent state management
- [ ] Decision routing logic

**Architecture**:
```
┌─────────────────────────────────────────────┐
│         Master Orchestrator                 │
│  (Analyzes task → Routes to best agent)     │
└─────────────────┬───────────────────────────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│  Local  │ │  Cloud  │ │  Tool   │
│   RAG   │ │  Agent  │ │ Agents  │
└─────────┘ └─────────┘ └─────────┘
      ↓           ↑
┌─────────────────────────┐
│  Path Mapping Service   │
│  (Bridges local/cloud)  │
└─────────────────────────┘
```

**Key Achievements**:
- Solves critical data schema mismatch between local and cloud storage
- Enables hybrid RAG: local retrieval + cloud LLM generation
- Privacy-preserving: only file IDs sent to cloud, not content
- High performance: O(1) translations with triple-index design

### Phase 3: Cloud Integration & Hybrid Reasoning 📋 PLANNED

**Goal**: Add selective cloud capabilities for complex tasks

**Planned Components**:
- [ ] Claude API integration
- [ ] Hybrid retrieval (local + cloud)
- [ ] Long-form reasoning pipelines
- [ ] External tool integrations (calendar, email, etc.)
- [ ] Privacy boundary enforcement
- [ ] Consent management system

**Privacy Mechanisms**:
- Explicit user consent before cloud calls
- Data minimization (only send necessary context)
- Audit log of cloud interactions
- Local fallback options
- Encrypted data transmission

### Phase 4: Unified Interface & Automation 🎯 FUTURE

**Goal**: Build user-facing interface and automation workflows

**Planned Components**:
- [ ] Web-based chat interface
- [ ] Voice interaction support
- [ ] Automation workflow designer
- [ ] Dashboard and analytics
- [ ] Mobile app integration
- [ ] Plugin system for extensibility

**User Experience**:
- Natural language interaction
- Proactive suggestions
- Transparent reasoning display
- Easy customization
- Privacy controls

## System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────┐
│                    User Interface                         │
│             (Chat, Voice, Automation)                     │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│              Master Orchestrator                          │
│  • Task Analysis      • Agent Routing                     │
│  • Context Management • Decision Making                   │
└───────────┬─────────────────────────┬────────────────────┘
            │                         │
    ┌───────▼──────────┐     ┌───────▼──────────┐
    │  Local Agents    │     │  Cloud Agents     │
    │  ─────────────   │     │  ──────────────   │
    │  • RAG Agent     │     │  • Claude API     │
    │  • Tool Agents   │     │  • Research Agent │
    │  • Quick Tasks   │     │  • Complex Tasks  │
    └──────────────────┘     └───────────────────┘
            │
    ┌───────▼──────────┐
    │  Data Layer      │
    │  ─────────────   │
    │  • Obsidian Vault│
    │  • Vector Store  │
    │  • Agent Memory  │
    │  • Preferences   │
    └──────────────────┘
```

### Agent Types

#### 1. Local RAG Agent (Phase 1) ✅
- **Purpose**: Privacy-preserving knowledge retrieval
- **Data**: Obsidian vault documents
- **Processing**: Fully local (CPU/GPU)
- **Latency**: Fast (<1 second)
- **Cost**: Free
- **Use Cases**:
  - "What are my notes on Project X?"
  - "Summarize my meeting from yesterday"
  - "Find information about topic Y"

#### 2. Tool Agents (Phase 2)
- **Purpose**: Specialized task execution
- **Examples**:
  - Calendar Agent: Schedule management
  - Email Agent: Email summarization and drafting
  - File Agent: Document operations
  - Web Agent: Controlled web search
- **Processing**: Local + API calls (with consent)

#### 3. Cloud Reasoning Agent (Phase 3)
- **Purpose**: Complex multi-step reasoning
- **Data**: Minimal context (user-approved)
- **Processing**: Claude API
- **Latency**: Moderate (2-5 seconds)
- **Cost**: Pay-per-use
- **Use Cases**:
  - "Analyze this business proposal and give me pros/cons"
  - "Create a project plan for initiative X"
  - "Draft a strategic memo on topic Y"

#### 4. Master Orchestrator (Phase 2)
- **Purpose**: Coordinate agents and route tasks
- **Logic**:
  ```
  If simple retrieval → Local RAG Agent
  If tool required → Specific Tool Agent
  If complex reasoning + user approved → Cloud Agent
  If uncertain → Ask user for clarification
  ```

## Data Flow & Privacy

### Privacy Tiers

**Tier 1: Fully Local** (Default)
- All processing on user's machine
- No external network calls
- Examples: RAG queries, simple tasks
- Privacy: Maximum

**Tier 2: Tool APIs** (With user setup)
- External APIs for specific tools
- User configures and authorizes
- Examples: Calendar sync, email access
- Privacy: User-controlled

**Tier 3: Cloud Reasoning** (Explicit consent)
- Minimal context sent to cloud
- User approves each operation
- Data minimization enforced
- Examples: Complex analysis, research
- Privacy: Transparent and controlled

### Consent Management

```python
# Example consent flow
async def execute_task(task, user_preferences):
    tier = assess_privacy_tier(task)

    if tier == PrivacyTier.LOCAL:
        return await local_agent.execute(task)

    elif tier == PrivacyTier.TOOL_API:
        if user_preferences.tools_authorized:
            return await tool_agent.execute(task)
        else:
            return await request_tool_authorization()

    elif tier == PrivacyTier.CLOUD:
        context = extract_minimal_context(task)
        if await request_user_consent(task, context):
            return await cloud_agent.execute(task, context)
        else:
            return await local_fallback(task)
```

## Technology Stack

### Phase 1 (Complete)
- **Language**: Python 3.11+
- **RAG Framework**: LlamaIndex
- **Vector Store**: FAISS (in-memory)
- **Embeddings**: HuggingFace (bge-small-en-v1.5)
- **Document Reader**: ObsidianReader
- **LLM**: Ollama (local inference)

### Phase 2 (In Progress)
- **Language**: Python 3.11+ (standard library only)
- **Path Mapping**: Custom triple-index architecture
- **Persistence**: JSON serialization
- **Cloud Storage**: Google Drive API (planned)

### Phase 3-4 (Planned)
- **Orchestration**: Custom Python framework
- **Cloud LLM**: Anthropic Claude API
- **Web Framework**: FastAPI
- **Frontend**: React + TypeScript
- **Database**: SQLite (local) + PostgreSQL (optional cloud)
- **Queue**: Redis (for background tasks)

## Directory Structure

```
Maestro/
├── agents/
│   ├── __init__.py
│   ├── AI_EXECUTIVE_ASSISTANT.md  (this file)
│   │
│   ├── local_rag/                  # Phase 1 ✅
│   │   ├── __init__.py
│   │   ├── local_rag_agent.py
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── cloud_integration/          # Phase 2 ✅ (Path Mapping)
│   │   ├── __init__.py
│   │   ├── path_mapping_service.py
│   │   └── README.md
│   │
│   ├── orchestrator/               # Phase 2 (planned)
│   │   ├── __init__.py
│   │   ├── master_orchestrator.py
│   │   ├── task_router.py
│   │   └── agent_registry.py
│   │
│   ├── cloud_agent/                # Phase 3 (planned)
│   │   ├── __init__.py
│   │   ├── claude_integration.py
│   │   └── consent_manager.py
│   │
│   └── tool_agents/                # Phase 2-3 (planned)
│       ├── __init__.py
│       ├── calendar_agent.py
│       ├── email_agent.py
│       └── web_agent.py
│
├── interface/                      # Phase 4 (planned)
│   ├── web/
│   │   ├── frontend/
│   │   └── backend/
│   └── cli/
│
└── shared/
    ├── models/
    ├── utils/
    └── config/
```

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints extensively
- Write comprehensive docstrings
- Add inline comments for complex logic

### Testing Strategy
- Unit tests for individual agents
- Integration tests for agent interactions
- End-to-end tests for user workflows
- Privacy compliance tests

### Documentation
- README for each module
- Inline code documentation
- Architecture decision records (ADRs)
- User guides and tutorials

### Privacy by Design
- Default to local processing
- Minimize data collection
- Explicit user consent
- Transparent operations
- Audit logging

## Getting Started

### Phase 1: Local RAG Agent

1. Clone the repository
2. Navigate to the local RAG agent:
   ```bash
   cd agents/local_rag
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the demonstration:
   ```bash
   python local_rag_agent.py
   ```

5. See detailed usage in `agents/local_rag/README.md`

### Phase 2: Path Mapping Service

1. Navigate to cloud integration:
   ```bash
   cd agents/cloud_integration
   ```

2. Run the demonstration (no dependencies needed - pure Python):
   ```bash
   python path_mapping_service.py
   ```

3. See detailed usage in `agents/cloud_integration/README.md`

4. Use in your code:
   ```python
   from agents.cloud_integration import PathMappingService

   service = PathMappingService()
   service.register_file('Projects/Plan.md', 'gdrive_id_123')
   gdrive_id = service.resolve_to_gdrive_id('Projects/Plan.md')
   ```

### Next Steps

- **For Developers**: Contribute to orchestrator design (next in Phase 2)
- **For Users**: Test with your Obsidian vault synced to Google Drive
- **For Researchers**: Explore hybrid local/cloud RAG architectures

## Success Metrics

### Phase 1 Metrics ✅
- [x] Successfully ingest Obsidian vault documents
- [x] Build and query vector index
- [x] Generate contextual responses
- [x] All processing happens locally
- [x] Response time < 2 seconds per query

### Phase 2 Metrics (In Progress)
- [x] O(1) path translation performance ✅
- [x] Bidirectional mapping (local ↔ cloud) ✅
- [x] Support bulk registration (efficient sync) ✅
- [x] JSON persistence for durability ✅
- [ ] Route 80%+ of tasks to appropriate agent (orchestrator - next)
- [ ] Support 5+ concurrent agent operations (orchestrator - next)
- [ ] Maintain context across multi-turn conversations (orchestrator - next)
- [ ] <100ms orchestration overhead (orchestrator - next)

### Phase 3 Metrics (Target)
- [ ] Cloud agent used for <20% of queries
- [ ] 100% user consent for cloud operations
- [ ] <5 second latency for cloud-augmented queries
- [ ] Zero unauthorized data transmissions

### Phase 4 Metrics (Target)
- [ ] Sub-second UI response times
- [ ] Support 10+ automation workflows
- [ ] 90%+ user satisfaction score
- [ ] Mobile-responsive interface

## Contributing

### Phase 2 Focus Areas

We're actively developing Phase 2 (Multi-Agent Orchestration). Contributions welcome in:

1. **Orchestrator Design**: Task decomposition and agent routing logic
2. **Agent Protocol**: Inter-agent communication standards
3. **State Management**: Context and memory across agent calls
4. **Testing**: Comprehensive test coverage for agent interactions

### How to Contribute

1. Review the Phase 2 plan above
2. Check existing issues or create a new one
3. Fork the repository
4. Create a feature branch
5. Submit a pull request with clear description

## References

### Papers & Research
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al.)
- "Local-First Software" (Kleppmann et al.)
- "Privacy-Preserving Machine Learning" (Fredrikson et al.)

### Tools & Frameworks
- [LlamaIndex](https://docs.llamaindex.ai/): RAG framework
- [FAISS](https://github.com/facebookresearch/faiss): Vector similarity search
- [Ollama](https://ollama.ai/): Local LLM inference
- [Obsidian](https://obsidian.md/): Knowledge management
- [Anthropic Claude](https://www.anthropic.com/): Cloud LLM API

### Inspiration
- Obsidian's data ownership philosophy
- Local-first software movement
- Privacy-focused AI initiatives
- Human-AI collaboration research

## FAQ

### Q: Why not just use ChatGPT or Claude directly?
**A**: Those are excellent tools, but they require sending all your data to the cloud. This system gives you the benefits of AI assistance while keeping sensitive information local.

### Q: How does local performance compare to cloud models?
**A**: For retrieval tasks, local RAG is actually faster (<1s vs 2-5s). For complex reasoning, cloud models are more capable, which is why we offer both options.

### Q: What about costs?
**A**: Local processing is free. Cloud operations use Claude API (pay-per-use), but the orchestrator minimizes cloud calls by handling most tasks locally.

### Q: Can I use this without Obsidian?
**A**: Yes! While optimized for Obsidian, you can adapt it for any markdown-based knowledge base or plain text files.

### Q: Is my data really private?
**A**: In Phase 1, absolutely—zero network calls. In later phases, you explicitly approve any cloud operations, and we use data minimization principles.

## License

[Specify License]

## Support & Contact

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: See individual module READMEs

---

**Project Status**: Phase 1 Complete ✅ | Phase 2 Path Mapping Complete ✅ | Orchestrator Next 🔄

**Last Updated**: 2025-11-08

**Next Milestone**: Phase 2 Multi-Agent Orchestrator Implementation
