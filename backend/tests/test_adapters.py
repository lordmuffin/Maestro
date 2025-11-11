"""Tests for LLM Adapters."""
import pytest
import json

from backend.core.skills.knowledge_search import SearchKnowledgeBaseSkill
from backend.core.skills.weekly_review import GenerateWeeklyReviewSkill
from backend.core.adapters import ClaudeAdapter, GeminiAdapter, OllamaAdapter


class TestClaudeAdapter:
    """Tests for ClaudeAdapter."""

    def test_convert_skill(self):
        """Test converting a skill to Claude format."""
        skill = SearchKnowledgeBaseSkill()
        adapter = ClaudeAdapter()

        claude_tool = adapter.convert_skill(skill)

        assert claude_tool["name"] == skill.name
        assert claude_tool["description"] == skill.description
        assert "input_schema" in claude_tool
        assert claude_tool["input_schema"]["type"] == "object"
        assert "properties" in claude_tool["input_schema"]
        assert "required" in claude_tool["input_schema"]

    def test_convert_multiple_skills(self):
        """Test converting multiple skills."""
        skills = [
            SearchKnowledgeBaseSkill(),
            GenerateWeeklyReviewSkill()
        ]
        adapter = ClaudeAdapter()

        claude_tools = adapter.convert_skills(skills)

        assert len(claude_tools) == 2
        assert all("name" in tool for tool in claude_tools)
        assert all("input_schema" in tool for tool in claude_tools)

    def test_parse_tool_use(self):
        """Test parsing Claude tool use response."""
        adapter = ClaudeAdapter()

        # Simulated Claude response
        response = {
            "content": [
                {
                    "type": "text",
                    "text": "I'll help you search."
                },
                {
                    "type": "tool_use",
                    "id": "toolu_01A09q90qw90",
                    "name": "search_knowledge_base",
                    "input": {
                        "query": "project updates",
                        "max_results": 5
                    }
                }
            ]
        }

        result = adapter.parse_tool_use(response)

        assert result["has_tool_calls"] is True
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search_knowledge_base"
        assert result["tool_calls"][0]["input"]["query"] == "project updates"

    def test_parse_no_tool_use(self):
        """Test parsing response with no tool use."""
        adapter = ClaudeAdapter()

        response = {
            "content": [
                {
                    "type": "text",
                    "text": "Here is my response."
                }
            ]
        }

        result = adapter.parse_tool_use(response)

        assert result["has_tool_calls"] is False
        assert len(result["tool_calls"]) == 0

    def test_format_tool_result(self):
        """Test formatting tool execution result."""
        adapter = ClaudeAdapter()

        result = adapter.format_tool_result(
            tool_call_id="toolu_123",
            result={"success": True, "data": "test"}
        )

        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "toolu_123"
        assert "content" in result

        # Content should be JSON string
        content_data = json.loads(result["content"])
        assert content_data["success"] is True


class TestGeminiAdapter:
    """Tests for GeminiAdapter."""

    def test_convert_skill(self):
        """Test converting a skill to Gemini format."""
        skill = GenerateWeeklyReviewSkill()
        adapter = GeminiAdapter()

        gemini_function = adapter.convert_skill(skill)

        assert gemini_function["name"] == skill.name
        assert gemini_function["description"] == skill.description
        assert "parameters" in gemini_function
        assert gemini_function["parameters"]["type"] == "OBJECT"

    def test_type_mapping(self):
        """Test JSON type to Gemini type mapping."""
        adapter = GeminiAdapter()

        assert adapter._map_type_to_gemini("string") == "STRING"
        assert adapter._map_type_to_gemini("integer") == "INTEGER"
        assert adapter._map_type_to_gemini("number") == "NUMBER"
        assert adapter._map_type_to_gemini("boolean") == "BOOLEAN"
        assert adapter._map_type_to_gemini("array") == "ARRAY"
        assert adapter._map_type_to_gemini("object") == "OBJECT"

    def test_convert_skills_with_arrays(self):
        """Test converting skills that have array parameters."""
        skill = GenerateWeeklyReviewSkill()  # Has array parameter
        adapter = GeminiAdapter()

        gemini_function = adapter.convert_skill(skill)
        properties = gemini_function["parameters"]["properties"]

        # Check include_sections array parameter
        assert "include_sections" in properties
        assert properties["include_sections"]["type"] == "ARRAY"
        assert "items" in properties["include_sections"]

    def test_format_function_response(self):
        """Test formatting function execution result."""
        adapter = GeminiAdapter()

        result = adapter.format_function_response(
            function_name="test_function",
            result={"success": True, "value": 42}
        )

        assert "function_response" in result
        assert result["function_response"]["name"] == "test_function"
        assert "response" in result["function_response"]


class TestOllamaAdapter:
    """Tests for OllamaAdapter."""

    def test_convert_skill(self):
        """Test converting a skill to Ollama format."""
        skill = SearchKnowledgeBaseSkill()
        adapter = OllamaAdapter()

        ollama_tool = adapter.convert_skill(skill)

        assert ollama_tool["type"] == "function"
        assert "function" in ollama_tool
        assert ollama_tool["function"]["name"] == skill.name
        assert ollama_tool["function"]["description"] == skill.description
        assert "parameters" in ollama_tool["function"]

    def test_convert_openai_compatible(self):
        """Test that Ollama format is OpenAI-compatible."""
        skill = GenerateWeeklyReviewSkill()
        adapter = OllamaAdapter()

        ollama_tool = adapter.convert_skill(skill)
        function = ollama_tool["function"]

        # Check OpenAI-compatible structure
        assert "name" in function
        assert "description" in function
        assert "parameters" in function
        assert function["parameters"]["type"] == "object"
        assert "properties" in function["parameters"]

    def test_parse_tool_call(self):
        """Test parsing Ollama tool call response."""
        adapter = OllamaAdapter()

        # Simulated Ollama response
        response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search_knowledge_base",
                            "arguments": json.dumps({
                                "query": "test",
                                "max_results": 3
                            })
                        }
                    }
                ]
            }
        }

        result = adapter.parse_tool_call(response)

        assert result["has_tool_calls"] is True
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search_knowledge_base"
        assert result["tool_calls"][0]["arguments"]["query"] == "test"

    def test_parse_invalid_json_arguments(self):
        """Test parsing tool call with invalid JSON arguments."""
        adapter = OllamaAdapter()

        response = {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "test_function",
                            "arguments": "invalid json {"
                        }
                    }
                ]
            }
        }

        result = adapter.parse_tool_call(response)

        # Should handle gracefully
        assert result["has_tool_calls"] is True
        assert result["tool_calls"][0]["arguments"] == {}

    def test_format_tool_result(self):
        """Test formatting tool execution result."""
        adapter = OllamaAdapter()

        result = adapter.format_tool_result(
            tool_call_id="call_123",
            tool_name="test_function",
            result={"success": True}
        )

        assert result["role"] == "tool"
        assert result["tool_call_id"] == "call_123"
        assert result["name"] == "test_function"
        assert "content" in result

        # Content should be JSON string
        content_data = json.loads(result["content"])
        assert content_data["success"] is True

    def test_supports_tools(self):
        """Test model tool support detection."""
        adapter = OllamaAdapter()

        # Models that support tools
        assert adapter.supports_tools("llama3.1:8b") is True
        assert adapter.supports_tools("mistral:7b") is True
        assert adapter.supports_tools("qwen2.5:14b") is True

        # Models that might not
        assert adapter.supports_tools("llama2:7b") is False
        assert adapter.supports_tools("codellama:7b") is False


class TestAdapterConsistency:
    """Tests for consistency across adapters."""

    def test_all_adapters_convert_same_skill(self):
        """Test that all adapters can convert the same skill."""
        skill = SearchKnowledgeBaseSkill()

        claude_adapter = ClaudeAdapter()
        gemini_adapter = GeminiAdapter()
        ollama_adapter = OllamaAdapter()

        # All should convert without errors
        claude_tool = claude_adapter.convert_skill(skill)
        gemini_tool = gemini_adapter.convert_skill(skill)
        ollama_tool = ollama_adapter.convert_skill(skill)

        # All should have the same skill name
        assert claude_tool["name"] == skill.name
        assert gemini_tool["name"] == skill.name
        assert ollama_tool["function"]["name"] == skill.name

    def test_parameter_consistency(self):
        """Test that parameters are consistent across adapters."""
        skill = GenerateWeeklyReviewSkill()

        claude_adapter = ClaudeAdapter()
        gemini_adapter = GeminiAdapter()
        ollama_adapter = OllamaAdapter()

        claude_tool = claude_adapter.convert_skill(skill)
        gemini_tool = gemini_adapter.convert_skill(skill)
        ollama_tool = ollama_adapter.convert_skill(skill)

        # Extract property names
        claude_props = set(claude_tool["input_schema"]["properties"].keys())
        gemini_props = set(gemini_tool["parameters"]["properties"].keys())
        ollama_props = set(ollama_tool["function"]["parameters"]["properties"].keys())

        # All should have the same parameters
        assert claude_props == gemini_props == ollama_props
