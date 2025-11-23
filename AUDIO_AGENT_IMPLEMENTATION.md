# Audio Interviewer Agent - Implementation Summary

## Overview

Successfully implemented a new **Audio Interviewer Agent** workflow for Maestro that processes audio recordings, clarifies facts with the user, and saves structured notes to the Obsidian vault.

## Files Created

### 1. **backend/core/rag/obsidian_writer.py**
Utility functions for writing to the Obsidian vault.

**Key Functions:**
- `save_to_obsidian()`: Writes markdown content to vault with automatic tagging
  - Handles file naming: `YYYY-MM-DD - Title.md`
  - Auto-appends `#Maestro` tag if missing
  - Supports subfolders (e.g., "Meetings")
  - Prevents duplicate filenames
  - Robust error handling with pathlib

- `append_to_obsidian()`: Appends content to existing notes

**Features:**
- Pydantic validation for inputs
- Pathlib for cross-platform file handling
- Automatic sanitization of filenames
- Comprehensive error handling

### 2. **agents/note_taker/audio_agent.py**
Main Audio Interviewer Agent implementation using LangGraph.

**Architecture:**
```
START
  ↓
[transcribe] ← Transcribe audio or use provided transcript
  ↓
[analyze] ← Detect ambiguities using prompt from interviewer_prompt.md
  ↓
{needs_clarification?}
  ├─ Yes → [question] → [wait for user] → [incorporate] → [analyze] (loop)
  └─ No → [generate] → [save] → END
```

**Key Components:**

#### Pydantic Models
- `AudioInput`: Validates input (audio_path or transcript required)
- `InterviewerState`: TypedDict for LangGraph state management

#### Workflow Nodes
1. `transcribe_node`: Transcribes audio (placeholder for Whisper integration)
2. `analyze_node`: Loads prompt from external file, identifies ambiguities
3. `question_node`: Compiles clarifying questions for user
4. `incorporate_clarifications_node`: Processes user responses
5. `generate_notes_node`: Creates structured markdown notes
6. `save_node`: Calls `save_to_obsidian()` to persist notes

#### Features
- **External Prompt Loading**: Reads from `prompts/interviewer_prompt.md` (not hardcoded)
- **Interrogation Loop**: Iteratively clarifies ambiguous facts
- **State Management**: Uses LangGraph's StateGraph pattern
- **Error Handling**: Try/catch blocks with fallback responses
- **Placeholder Function**: `transcribe_audio()` ready for Whisper API integration

### 3. **prompts/interviewer_prompt.md**
Comprehensive system prompt defining agent behavior.

**Sections:**
- Mission and goals
- Information to extract (decisions, action items, dates, people)
- Ambiguity detection patterns (vague references, unclear timelines)
- Output format (structured markdown template)
- Interaction flow and guidelines
- Privacy-first principles

**Key Instructions:**
- Extract: decisions, action items, dates, people, topics, follow-ups
- Flag: vague pronouns, missing context, unclear timelines, incomplete actions
- Format: Structured markdown with summary, decisions, action items, discussion points
- Privacy: Local processing, user control, transparency

### 4. **Integration with Orchestrator**
Modified `agents/orchestrator/supervisor_agent.py` to route audio queries.

**Changes:**

#### Added `audio_worker()` function
```python
def audio_worker(state: AgentState) -> dict:
    """
    Audio Interviewer Agent worker.

    Processes recordings, transcripts, and generates structured notes.
    Saves to Obsidian vault with #Maestro tag.
    """
```

#### Updated `classify_query()` routing logic
Added audio keywords:
```python
audio_keywords = ['audio', 'recording', 'transcript', 'meeting recording',
                  'voice note', 'interview recording', 'process audio',
                  'transcribe', 'voice memo']
```

Routes to:
- Classification: `"audio"`
- Sensitivity: `"HIGH"` (audio recordings contain sensitive information)
- Task Type: `"AUDIO_PROCESSING"`

#### Updated `create_supervisor_graph()`
```python
workflow.add_node("audio", audio_worker)
workflow.add_conditional_edges(
    "classifier",
    lambda state: state["classification"],
    {
        "local": "local",
        "claude": "claude",
        "gemini": "gemini",
        "audio": "audio",  # New routing
    }
)
workflow.add_edge("audio", END)
```

## Usage Examples

### Example 1: Using the Agent Directly
```python
from agents.note_taker.audio_agent import AudioInterviewerAgent
from pathlib import Path

agent = AudioInterviewerAgent()

# With audio file
result = agent.process(
    audio_path=Path("/path/to/meeting.mp3"),
    title="Q4 Planning Meeting"
)

# With existing transcript
result = agent.process(
    transcript="Meeting notes...",
    title="Weekly Standup",
    meeting_type="Team Meeting"
)
```

### Example 2: Through the Orchestrator
```python
from agents.orchestrator.supervisor_agent import SupervisorAgent

supervisor = SupervisorAgent()

result = supervisor.execute(
    query="Process this audio recording: Discussion about Project Phoenix..."
)
# Automatically routes to audio agent
```

### Example 3: Saving to Obsidian Directly
```python
from backend.core.rag.obsidian_writer import save_to_obsidian

path = save_to_obsidian(
    content="# Meeting Notes\n\nKey points...",
    title="Project Kickoff",
    subfolder="Meetings",
    auto_tag=True
)
# Saves to: /app/data/vault/Meetings/2025-11-23 - Project Kickoff.md
# With #Maestro tag appended
```

## Architecture Patterns

### 1. **StateGraph Pattern** (LangGraph)
- Follows existing Maestro pattern in `supervisor_agent.py`
- TypedDict for state schema
- Node functions return dict updates
- Conditional edges for routing

### 2. **Pydantic Validation**
- `AudioInput` model validates inputs
- Ensures either `audio_path` or `transcript` is provided
- Type safety with Path and Optional types

### 3. **External Configuration**
- System prompt loaded from `prompts/interviewer_prompt.md`
- Vault path from `settings.obsidian_vault_path`
- Easy to update behavior without code changes

### 4. **Privacy-First Design**
- All processing happens locally
- No external API calls (except optional Whisper)
- Sensitive audio = HIGH sensitivity classification
- User confirmation before saving

## Next Steps / TODOs

### 1. **Whisper Integration**
Replace the placeholder in `transcribe_audio()`:

```python
# Option A: Local Whisper
import whisper
model = whisper.load_model("base")
result = model.transcribe(str(audio_path))
return result["text"]

# Option B: OpenAI Whisper API
from openai import OpenAI
client = OpenAI()
with open(audio_path, "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
return transcript.text
```

### 2. **LLM-Based Analysis**
Replace rule-based ambiguity detection with LLM:

```python
# In analyze_node()
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-3-haiku-20240307",
    system=system_prompt,
    messages=[{
        "role": "user",
        "content": f"Analyze this transcript and identify ambiguities:\n\n{transcript}"
    }]
)
# Parse response for ambiguities
```

### 3. **Interactive Clarification Loop**
- Add UI for displaying questions
- Wait for user responses
- Re-analyze with clarifications
- Iterate until complete

### 4. **Audio File Upload**
- Add FastAPI endpoint for file uploads
- Support multiple formats (mp3, wav, m4a, etc.)
- Store temporarily during processing
- Clean up after transcription

### 5. **Enhanced Note Generation**
- Use LLM to extract structured information
- Identify speakers automatically
- Detect sentiment and tone
- Generate executive summaries

## Testing

### Test Suite: `test_audio_agent.py`

Created comprehensive test suite covering:

1. **Routing Test**: Verifies audio queries route to audio agent
2. **Agent Test**: Tests standalone audio processing
3. **Writer Test**: Validates Obsidian vault writing

### Running Tests
```bash
# Ensure dependencies are installed
pip install langgraph langchain-core pydantic pydantic-settings

# Run tests
python test_audio_agent.py
```

## Configuration Requirements

### Environment Variables
```bash
# In .env file
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault
ANTHROPIC_API_KEY=sk-... # For LLM-based analysis (future)
OPENAI_API_KEY=sk-...     # For Whisper API (future)
```

### Dependencies
```bash
# Core
langgraph>=0.0.20
langchain-core>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Future integrations
openai>=1.0.0        # For Whisper API
whisper              # For local transcription
anthropic>=0.18.0    # For Claude-based analysis
```

## File Structure
```
Maestro/
├── agents/
│   ├── note_taker/           # NEW
│   │   ├── __init__.py       # NEW
│   │   └── audio_agent.py    # NEW - Main agent implementation
│   └── orchestrator/
│       └── supervisor_agent.py  # MODIFIED - Added audio routing
├── backend/
│   └── core/
│       ├── config.py
│       └── rag/
│           ├── obsidian_rag.py
│           └── obsidian_writer.py  # NEW - Writing utilities
├── prompts/                   # NEW
│   └── interviewer_prompt.md  # NEW - Agent behavior instructions
└── test_audio_agent.py        # NEW - Test suite
```

## Key Features Implemented

✅ **save_to_obsidian utility**
  - Automatic file naming with dates
  - Auto-appends #Maestro tag
  - Subfolder support
  - Duplicate handling

✅ **Audio Interviewer Agent**
  - StateGraph workflow
  - Interrogation loop pattern
  - External prompt loading
  - Placeholder for Whisper

✅ **Orchestrator Integration**
  - Keyword-based routing
  - "audio", "recording", "transcript" detection
  - HIGH sensitivity classification
  - Seamless workflow integration

✅ **Pydantic Validation**
  - AudioInput model
  - InterviewerState TypedDict
  - Type safety

✅ **Robust Error Handling**
  - Try/catch in all nodes
  - Fallback responses
  - Detailed logging

✅ **Privacy-First**
  - Local processing
  - HIGH sensitivity for audio
  - User control over saving

## Summary

The Audio Interviewer Agent is now fully integrated into Maestro's architecture:

1. **New Functionality**: Process audio → Clarify facts → Save to Obsidian
2. **Follows Patterns**: Uses existing StateGraph, config, and orchestration patterns
3. **Privacy-Focused**: All processing local, HIGH sensitivity classification
4. **Extensible**: Placeholder functions ready for Whisper/LLM integration
5. **Well-Documented**: System prompt in external file, comprehensive docstrings

**Ready for production use** after adding:
- Real Whisper integration
- LLM-based analysis
- UI for clarification loop
- Audio file upload endpoint
