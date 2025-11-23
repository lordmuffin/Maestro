"""
Audio Interviewer Agent - Processes audio recordings and creates structured notes.

This agent implements an "Interrogation Loop" workflow:
1. Transcribe audio (or accept transcript)
2. Analyze for ambiguities and missing facts
3. Ask clarifying questions to the user
4. Refine understanding based on user responses
5. Generate structured notes
6. Save to Obsidian vault with #Maestro tag
"""

from typing import TypedDict, Optional, Literal, Any, Dict
from pathlib import Path
from pydantic import BaseModel, Field, validator
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from backend.core.rag.obsidian_writer import save_to_obsidian

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Data Validation
# ============================================================================

class AudioInput(BaseModel):
    """Input for audio processing."""

    audio_path: Optional[Path] = Field(None, description="Path to audio file")
    transcript: Optional[str] = Field(None, description="Pre-existing transcript")
    title: Optional[str] = Field(None, description="Title for the notes")
    meeting_type: Optional[str] = Field("Meeting", description="Type of recording")

    @validator('transcript', 'audio_path')
    def check_input(cls, v, values, field):
        """Ensure at least one input is provided."""
        if field.name == 'transcript':
            if not v and not values.get('audio_path'):
                raise ValueError("Either audio_path or transcript must be provided")
        return v

    class Config:
        arbitrary_types_allowed = True


class InterviewerState(TypedDict):
    """
    State schema for the Audio Interviewer workflow.

    This state is passed through the LangGraph workflow, tracking the
    interrogation loop's progress.
    """
    # Input
    audio_path: Optional[Path]
    transcript: Optional[str]
    title: Optional[str]
    meeting_type: Optional[str]

    # Processing
    raw_transcript: Optional[str]
    analysis: Optional[Dict[str, Any]]
    ambiguities: Optional[list]
    clarifications: Optional[Dict[str, str]]

    # Loop control
    needs_clarification: bool
    user_response: Optional[str]
    iteration_count: int

    # Output
    structured_notes: Optional[str]
    saved_path: Optional[Path]
    status: str  # "transcribing", "analyzing", "questioning", "complete", "error"
    error: Optional[str]

    # Metadata
    metadata: Optional[Dict[str, Any]]


# ============================================================================
# Placeholder Function - To be replaced with actual implementation
# ============================================================================

def transcribe_audio(audio_path: Path) -> str:
    """
    Placeholder for audio transcription.

    TODO: Implement with Whisper API or local Whisper model.

    Args:
        audio_path: Path to audio file (mp3, wav, m4a, etc.)

    Returns:
        str: Transcribed text

    Example Integration (when ready):
        ```python
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path))
        return result["text"]
        ```

    Or with OpenAI Whisper API:
        ```python
        from openai import OpenAI
        client = OpenAI()
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
        ```
    """
    logger.warning(f"transcribe_audio is a placeholder. Audio file: {audio_path}")

    # Return a sample transcript for testing
    return f"""[PLACEHOLDER TRANSCRIPT]

This is a placeholder transcript from the audio file: {audio_path.name}

In production, this would contain the actual transcribed content from the audio.

Sample content:
- Discussed Q4 roadmap for Project Phoenix
- John agreed to complete the API design by end of month
- Need to schedule follow-up with the engineering team
- Budget concerns were raised but not resolved
"""


# ============================================================================
# Workflow Node Functions
# ============================================================================

def transcribe_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 1: Transcribe audio if needed.

    If transcript is already provided, skip transcription.
    Otherwise, call transcribe_audio() on the audio file.
    """
    logger.info("🎤 Transcription Node")

    # If transcript already exists, use it
    if state.get('transcript'):
        logger.info("   Using provided transcript")
        return {
            "raw_transcript": state['transcript'],
            "status": "analyzing"
        }

    # If audio path provided, transcribe it
    if state.get('audio_path'):
        audio_path = state['audio_path']
        logger.info(f"   Transcribing audio: {audio_path}")

        try:
            transcript = transcribe_audio(audio_path)
            return {
                "raw_transcript": transcript,
                "status": "analyzing"
            }
        except Exception as e:
            logger.error(f"   Transcription failed: {e}")
            return {
                "status": "error",
                "error": f"Transcription failed: {str(e)}"
            }

    # No input provided
    return {
        "status": "error",
        "error": "No audio path or transcript provided"
    }


def load_interviewer_prompt() -> str:
    """
    Load the interviewer system prompt from external file.

    Returns:
        str: System prompt content
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "interviewer_prompt.md"

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load interviewer prompt: {e}")
        # Fallback prompt
        return """You are an AI interviewer. Analyze the transcript and identify ambiguities.
Ask clarifying questions, then generate structured notes."""


def analyze_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 2: Analyze transcript for ambiguities.

    Loads the behavior instructions from prompts/interviewer_prompt.md
    and uses an LLM to identify facts that need clarification.
    """
    logger.info("🔍 Analysis Node")

    transcript = state.get('raw_transcript', '')
    user_clarifications = state.get('clarifications', {})

    # Load system prompt
    system_prompt = load_interviewer_prompt()

    # TODO: Replace with actual LLM call
    # For now, simulate analysis with rule-based detection
    ambiguities = []

    # Simple heuristic: look for vague pronouns and unclear references
    vague_patterns = ['he ', 'she ', 'they ', 'it ', 'them ', 'next week', 'soon', 'later']

    for pattern in vague_patterns:
        if pattern in transcript.lower():
            ambiguities.append({
                "type": "vague_reference",
                "pattern": pattern.strip(),
                "question": f"Who/what does '{pattern.strip()}' refer to in the transcript?"
            })

    # Check if we have unanswered ambiguities
    unanswered = [amb for amb in ambiguities if amb['pattern'] not in user_clarifications]

    logger.info(f"   Found {len(ambiguities)} potential ambiguities")
    logger.info(f"   {len(unanswered)} still need clarification")

    if unanswered:
        return {
            "analysis": {
                "system_prompt": system_prompt,
                "transcript_length": len(transcript),
                "analyzed_at": datetime.now().isoformat()
            },
            "ambiguities": unanswered,
            "needs_clarification": True,
            "status": "questioning"
        }
    else:
        # No ambiguities or all clarified - move to generation
        return {
            "analysis": {
                "system_prompt": system_prompt,
                "transcript_length": len(transcript),
                "analyzed_at": datetime.now().isoformat()
            },
            "ambiguities": [],
            "needs_clarification": False,
            "status": "generating"
        }


def question_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 3: Ask clarifying questions to the user.

    This node compiles questions from detected ambiguities and
    returns them to the user for response.
    """
    logger.info("❓ Question Node")

    ambiguities = state.get('ambiguities', [])

    if not ambiguities:
        logger.info("   No questions needed")
        return {
            "needs_clarification": False,
            "status": "generating"
        }

    # Format questions for the user
    questions = []
    for i, amb in enumerate(ambiguities[:5], 1):  # Limit to 5 questions at a time
        questions.append(f"{i}. {amb['question']}")

    questions_text = "\n".join(questions)

    logger.info(f"   Prepared {len(questions)} questions for user")

    # In a real implementation, this would:
    # 1. Return questions to the UI/user
    # 2. Wait for user response
    # 3. Continue workflow with user input

    return {
        "status": "awaiting_user_input",
        "metadata": {
            "questions": questions_text,
            "question_count": len(questions)
        }
    }


def incorporate_clarifications_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 4: Incorporate user's clarifications into the state.

    This node processes the user's responses and updates the clarifications.
    """
    logger.info("💬 Incorporating Clarifications")

    user_response = state.get('user_response', '')
    existing_clarifications = state.get('clarifications', {})
    ambiguities = state.get('ambiguities', [])

    # TODO: Parse user response and map to ambiguities
    # For now, just store the raw response

    # Increment iteration count
    iteration = state.get('iteration_count', 0) + 1

    # Simple logic: assume after user responds, we're done (in real impl, would re-analyze)
    return {
        "clarifications": {**existing_clarifications, "user_input": user_response},
        "iteration_count": iteration,
        "needs_clarification": False,
        "status": "generating"
    }


def generate_notes_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 5: Generate structured notes from clarified transcript.

    Uses the system prompt and clarified information to create
    well-formatted notes ready for Obsidian.
    """
    logger.info("📝 Generating Structured Notes")

    transcript = state.get('raw_transcript', '')
    clarifications = state.get('clarifications', {})
    title = state.get('title', 'Meeting Notes')
    meeting_type = state.get('meeting_type', 'Meeting')

    # TODO: Replace with actual LLM generation
    # For now, create a simple structured format

    date_str = datetime.now().strftime("%Y-%m-%d")

    notes = f"""# {title}

**Date**: {date_str}
**Type**: {meeting_type}
**Processed by**: Maestro Audio Interviewer Agent

## Summary

{transcript[:200]}...

## Key Points

- [Point 1 - to be extracted by LLM]
- [Point 2 - to be extracted by LLM]

## Action Items

- [ ] [Action 1] - **Owner**: TBD - **Due**: TBD

## Clarifications

"""

    # Add clarifications
    for key, value in clarifications.items():
        notes += f"- {key}: {value}\n"

    notes += """
## Notes

[Additional notes to be generated by LLM]

## Raw Transcript

<details>
<summary>Click to expand</summary>

{transcript}

</details>
"""

    notes = notes.format(transcript=transcript)

    logger.info("   Structured notes generated successfully")

    return {
        "structured_notes": notes,
        "status": "ready_to_save",
        "metadata": {
            **state.get('metadata', {}),
            "generated_at": datetime.now().isoformat()
        }
    }


def save_node(state: InterviewerState) -> Dict[str, Any]:
    """
    Node 6: Save the structured notes to Obsidian vault.

    Calls save_to_obsidian utility with proper formatting and tagging.
    """
    logger.info("💾 Saving to Obsidian")

    notes = state.get('structured_notes', '')
    title = state.get('title', 'Meeting Notes')

    try:
        # Save to Obsidian vault in a "Meetings" subfolder
        saved_path = save_to_obsidian(
            content=notes,
            title=title,
            subfolder="Meetings",
            auto_tag=True,
            tag="Maestro"
        )

        logger.info(f"   ✅ Saved successfully to: {saved_path}")

        return {
            "saved_path": saved_path,
            "status": "complete",
            "metadata": {
                **state.get('metadata', {}),
                "saved_at": datetime.now().isoformat(),
                "file_path": str(saved_path)
            }
        }

    except Exception as e:
        logger.error(f"   ❌ Save failed: {e}")
        return {
            "status": "error",
            "error": f"Failed to save to Obsidian: {str(e)}"
        }


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def should_ask_questions(state: InterviewerState) -> str:
    """
    Determine if we need to ask clarifying questions.

    Returns:
        "question" if clarification needed, "generate" otherwise
    """
    needs_clarification = state.get('needs_clarification', False)

    if needs_clarification:
        return "question"
    else:
        return "generate"


def should_save(state: InterviewerState) -> str:
    """
    Determine if notes are ready to save.

    In production, this would check for user confirmation.
    For now, auto-save when notes are generated.

    Returns:
        "save" if ready, "end" otherwise
    """
    status = state.get('status', '')

    if status == 'ready_to_save':
        return "save"
    else:
        return "end"


# ============================================================================
# LangGraph Workflow Setup
# ============================================================================

def create_interviewer_graph() -> StateGraph:
    """
    Create the LangGraph StateGraph for audio interviewing workflow.

    Workflow:
        START
          ↓
        [transcribe] ← Transcribe audio or use provided transcript
          ↓
        [analyze] ← Detect ambiguities using prompt
          ↓
        {needs_clarification?}
          ├─ Yes → [question] → [wait for user] → [incorporate] → [analyze]
          └─ No → [generate] → [save] → END
    """
    workflow = StateGraph(InterviewerState)

    # Add nodes
    workflow.add_node("transcribe", transcribe_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("question", question_node)
    workflow.add_node("incorporate", incorporate_clarifications_node)
    workflow.add_node("generate", generate_notes_node)
    workflow.add_node("save", save_node)

    # Set entry point
    workflow.set_entry_point("transcribe")

    # Add edges
    workflow.add_edge("transcribe", "analyze")

    # Conditional: ask questions or generate?
    workflow.add_conditional_edges(
        "analyze",
        should_ask_questions,
        {
            "question": "question",
            "generate": "generate"
        }
    )

    # Question node waits for user input (in real implementation)
    # For demo, we skip to incorporate
    workflow.add_edge("question", "incorporate")
    workflow.add_edge("incorporate", "analyze")  # Loop back to re-analyze

    # After generation, decide whether to save
    workflow.add_conditional_edges(
        "generate",
        should_save,
        {
            "save": "save",
            "end": END
        }
    )

    # After saving, we're done
    workflow.add_edge("save", END)

    return workflow.compile()


# ============================================================================
# AudioInterviewerAgent Class (API Wrapper)
# ============================================================================

class AudioInterviewerAgent:
    """
    Audio Interviewer Agent for processing recordings and creating notes.

    This agent implements the interrogation loop pattern:
    1. Transcribe audio
    2. Analyze for ambiguities
    3. Ask clarifying questions
    4. Generate structured notes
    5. Save to Obsidian

    Example:
        ```python
        agent = AudioInterviewerAgent()

        # With audio file
        result = agent.process(audio_path=Path("meeting.mp3"), title="Q4 Planning")

        # With existing transcript
        result = agent.process(transcript="Meeting notes...", title="Standup")
        ```
    """

    def __init__(self):
        """Initialize the Audio Interviewer Agent."""
        self.graph = create_interviewer_graph()
        logger.info("AudioInterviewerAgent initialized")

    def process(
        self,
        audio_path: Optional[Path] = None,
        transcript: Optional[str] = None,
        title: Optional[str] = None,
        meeting_type: str = "Meeting",
        user_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an audio recording or transcript.

        Args:
            audio_path: Path to audio file
            transcript: Pre-existing transcript text
            title: Title for the notes
            meeting_type: Type of recording (Meeting, Interview, etc.)
            user_response: User's response to clarifying questions

        Returns:
            dict: Result with status, notes, and saved path
        """
        # Validate input
        audio_input = AudioInput(
            audio_path=audio_path,
            transcript=transcript,
            title=title,
            meeting_type=meeting_type
        )

        # Initialize state
        initial_state: InterviewerState = {
            "audio_path": audio_input.audio_path,
            "transcript": audio_input.transcript,
            "title": audio_input.title or "Meeting Notes",
            "meeting_type": audio_input.meeting_type,
            "raw_transcript": None,
            "analysis": None,
            "ambiguities": None,
            "clarifications": {},
            "needs_clarification": False,
            "user_response": user_response,
            "iteration_count": 0,
            "structured_notes": None,
            "saved_path": None,
            "status": "transcribing",
            "error": None,
            "metadata": {}
        }

        # Execute workflow
        try:
            result = self.graph.invoke(initial_state)

            return {
                "status": result.get("status", "unknown"),
                "notes": result.get("structured_notes"),
                "saved_path": str(result.get("saved_path")) if result.get("saved_path") else None,
                "questions": result.get("metadata", {}).get("questions"),
                "error": result.get("error"),
                "metadata": result.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Audio processing failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "notes": None,
                "saved_path": None
            }


# ============================================================================
# Demo / Testing
# ============================================================================

def main():
    """Demo the Audio Interviewer Agent."""
    print("="*80)
    print("AUDIO INTERVIEWER AGENT - DEMO")
    print("="*80)

    agent = AudioInterviewerAgent()

    # Test with sample transcript
    sample_transcript = """
    Meeting with John Smith about Project Phoenix.
    He said we need to finish the API design by end of month.
    The team should schedule a follow-up meeting soon.
    Budget was discussed but they couldn't reach a decision.
    """

    print("\n📝 Processing sample transcript...")
    result = agent.process(
        transcript=sample_transcript,
        title="Project Phoenix Planning",
        meeting_type="Team Meeting"
    )

    print(f"\n✅ Status: {result['status']}")
    if result.get('questions'):
        print(f"\n❓ Questions:\n{result['questions']}")
    if result.get('notes'):
        print(f"\n📄 Generated Notes:\n{result['notes'][:500]}...")
    if result.get('saved_path'):
        print(f"\n💾 Saved to: {result['saved_path']}")
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
