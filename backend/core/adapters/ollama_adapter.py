"""Adapter for converting EA Skills to Ollama tool format."""
from typing import List, Dict, Any
from backend.core.skills.base import EASkill
import logging

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """
    Adapter for Ollama tool calling format.

    Ollama supports tool calling (function calling) similar to OpenAI's format.
    This adapter converts EA Skills to Ollama-compatible tool definitions.

    Note: Tool calling support in Ollama may vary by model. Best supported by:
    - Llama 3.1 and later
    - Mistral models with tool support
    - Other models with function calling capabilities
    """

    @staticmethod
    def convert_skill(skill: EASkill) -> Dict[str, Any]:
        """
        Convert EA Skill to Ollama tool format.

        Args:
            skill: EA Skill instance

        Returns:
            Ollama tool definition (OpenAI-compatible format)

        Example output:
        {
            "type": "function",
            "function": {
                "name": "generate_project_synthesis",
                "description": "Generate comprehensive project synthesis...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "The name of the project..."
                        },
                        ...
                    },
                    "required": ["project_name"]
                }
            }
        }
        """
        # Get JSON schema from Pydantic model
        pydantic_schema = skill.input_schema.model_json_schema()

        # Extract and clean properties
        properties = {}
        for prop_name, prop_schema in pydantic_schema.get("properties", {}).items():
            cleaned_prop = {
                "type": prop_schema.get("type", "string"),
                "description": prop_schema.get("description", f"Parameter: {prop_name}")
            }

            # Handle enums
            if "enum" in prop_schema:
                cleaned_prop["enum"] = prop_schema["enum"]

            # Handle arrays
            if cleaned_prop["type"] == "array" and "items" in prop_schema:
                cleaned_prop["items"] = prop_schema["items"]

            # Handle defaults
            if "default" in prop_schema:
                cleaned_prop["default"] = prop_schema["default"]

            properties[prop_name] = cleaned_prop

        # Build Ollama tool schema (OpenAI-compatible)
        ollama_tool = {
            "type": "function",
            "function": {
                "name": skill.name,
                "description": skill.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": pydantic_schema.get("required", [])
                }
            }
        }

        logger.debug(f"Converted skill '{skill.name}' for Ollama")
        return ollama_tool

    @staticmethod
    def convert_skills(skills: List[EASkill]) -> List[Dict[str, Any]]:
        """
        Convert multiple skills.

        Args:
            skills: List of EA Skills

        Returns:
            List of Ollama tool definitions
        """
        return [OllamaAdapter.convert_skill(skill) for skill in skills]

    @staticmethod
    def parse_tool_call(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ollama's tool call response.

        Args:
            response: Ollama API response

        Returns:
            Parsed tool call information

        Example Ollama response with tool call:
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "generate_project_synthesis",
                            "arguments": "{\"project_name\": \"AI_Assistant\"}"
                        }
                    }
                ]
            }
        }
        """
        import json

        tool_calls = []

        try:
            message = response.get("message", {})
            raw_tool_calls = message.get("tool_calls", [])

            for tc in raw_tool_calls:
                if tc.get("type") == "function":
                    function = tc.get("function", {})
                    args_str = function.get("arguments", "{}")

                    # Parse arguments JSON
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse arguments: {args_str}")
                        args = {}

                    tool_calls.append({
                        "id": tc.get("id"),
                        "name": function.get("name"),
                        "arguments": args
                    })

        except Exception as e:
            logger.error(f"Failed to parse Ollama response: {e}")

        return {
            "has_tool_calls": len(tool_calls) > 0,
            "tool_calls": tool_calls
        }

    @staticmethod
    def format_tool_result(
        tool_call_id: str,
        tool_name: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format tool execution result for Ollama.

        Args:
            tool_call_id: ID of the tool call
            tool_name: Name of the tool that was called
            result: Result from skill execution

        Returns:
            Formatted tool result for Ollama (OpenAI-compatible)
        """
        import json

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(result)
        }

    @staticmethod
    def supports_tools(model_name: str) -> bool:
        """
        Check if a specific Ollama model supports tool calling.

        Args:
            model_name: Name of the Ollama model

        Returns:
            True if model likely supports tools
        """
        # Models known to support tool calling
        supported_patterns = [
            "llama3.1",
            "llama3.2",
            "llama3.3",
            "mistral",
            "mixtral",
            "qwen2.5",
            "command-r"
        ]

        model_lower = model_name.lower()
        return any(pattern in model_lower for pattern in supported_patterns)
