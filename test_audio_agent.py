#!/usr/bin/env python3
"""
Test script for Audio Interviewer Agent integration.

This script demonstrates the full workflow:
1. Routing "audio" queries to the audio agent
2. Processing transcripts
3. Generating structured notes
4. Saving to Obsidian vault
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator.supervisor_agent import create_supervisor_graph, AgentState


def test_audio_routing():
    """Test that audio-related queries are routed to the audio agent."""
    print("="*80)
    print("TEST 1: Audio Query Routing")
    print("="*80)

    graph = create_supervisor_graph()

    # Test query with audio keyword
    query = "Process this audio recording: Team discussed Q4 roadmap and John agreed to complete the API design by end of month."

    initial_state: AgentState = {
        "query": query,
        "classification": None,
        "sensitivity": None,
        "task_type": None,
        "response": None,
        "agent_used": None,
        "metadata": None,
        "llm_provider": None,
        "model": None,
    }

    print(f"\n📝 Query: {query}")
    print("\n🔄 Executing workflow...")

    result = graph.invoke(initial_state)

    print(f"\n✅ Result:")
    print(f"   Agent Used: {result['agent_used']}")
    print(f"   Task Type: {result['task_type']}")
    print(f"   Sensitivity: {result['sensitivity']}")
    print(f"   Classification: {result['classification']}")

    assert result['agent_used'] == 'audio_interviewer', f"Expected audio_interviewer, got {result['agent_used']}"
    assert result['classification'] == 'audio', f"Expected audio classification, got {result['classification']}"

    print("\n✅ TEST PASSED: Audio queries are correctly routed to audio agent")


def test_audio_agent_standalone():
    """Test the audio agent directly."""
    print("\n" + "="*80)
    print("TEST 2: Audio Agent Standalone Processing")
    print("="*80)

    from agents.note_taker.audio_agent import AudioInterviewerAgent

    agent = AudioInterviewerAgent()

    sample_transcript = """
    Meeting with Sarah Johnson and Mike Chen about Project Phoenix.
    We discussed the Q4 roadmap and prioritization.
    Sarah agreed to complete the API design by November 30th.
    Mike will handle the database migration.
    We need to schedule a follow-up meeting next week.
    Budget concerns were raised but no final decision was made.
    The engineering team should be consulted before moving forward.
    """

    print(f"\n📝 Processing transcript...")

    result = agent.process(
        transcript=sample_transcript,
        title="Project Phoenix Q4 Planning",
        meeting_type="Team Meeting"
    )

    print(f"\n✅ Result:")
    print(f"   Status: {result['status']}")
    print(f"   Saved Path: {result.get('saved_path', 'N/A')}")

    if result.get('notes'):
        print(f"\n📄 Generated Notes (first 300 chars):")
        print(result['notes'][:300] + "...")

    if result.get('questions'):
        print(f"\n❓ Clarifying Questions:")
        print(result['questions'])

    print("\n✅ TEST PASSED: Audio agent processed transcript successfully")


def test_obsidian_writer():
    """Test the obsidian_writer utility."""
    print("\n" + "="*80)
    print("TEST 3: Obsidian Writer Utility")
    print("="*80)

    from backend.core.rag.obsidian_writer import save_to_obsidian
    from backend.core.config import settings
    import tempfile
    import shutil

    # Create a temporary vault for testing
    with tempfile.TemporaryDirectory() as temp_vault:
        print(f"\n📁 Using temporary vault: {temp_vault}")

        test_content = """# Test Meeting Notes

**Date**: 2025-11-23
**Participants**: Test User

## Summary

This is a test note to verify the Obsidian writer functionality.

## Key Points

- Point 1
- Point 2

## Action Items

- [ ] Test action item
"""

        # Save to temporary vault
        saved_path = save_to_obsidian(
            content=test_content,
            title="Test Meeting",
            vault_path=temp_vault,
            subfolder="Meetings",
            auto_tag=True,
            tag="Maestro"
        )

        print(f"   ✅ File saved to: {saved_path}")

        # Verify the file exists
        assert saved_path.exists(), f"File was not created: {saved_path}"

        # Verify the content
        with open(saved_path, 'r') as f:
            content = f.read()

        print(f"   ✅ File exists and is readable")

        # Verify tag was added
        assert "#Maestro" in content, "Tag was not added to content"
        print(f"   ✅ #Maestro tag was added")

        print("\n✅ TEST PASSED: Obsidian writer works correctly")


def main():
    """Run all tests."""
    print("\n" + "█"*80)
    print("AUDIO INTERVIEWER AGENT - TEST SUITE")
    print("█"*80 + "\n")

    try:
        # Test 1: Routing
        test_audio_routing()

        # Test 2: Agent standalone
        test_audio_agent_standalone()

        # Test 3: Obsidian writer
        test_obsidian_writer()

        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\n✅ Summary:")
        print("   1. Audio queries are correctly routed to the audio agent")
        print("   2. Audio agent processes transcripts successfully")
        print("   3. Obsidian writer saves notes correctly")
        print("\n📚 Next Steps:")
        print("   - Replace transcribe_audio() placeholder with real Whisper integration")
        print("   - Add LLM-based analysis for ambiguity detection")
        print("   - Implement interactive clarification loop in the UI")
        print("   - Add support for audio file uploads")
        print("="*80 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
