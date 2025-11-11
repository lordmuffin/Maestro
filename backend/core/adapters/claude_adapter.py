"""Adapter for converting EA Skills to Claude tool format."""
from typing import List, Dict, Any
from backend.core.skills.base import EASkill
import logging

logger = logging.getLogger(__name__)


class ClaudeAdapter:
    """
    Adapter for Anthropic Claude API tool use format.

    Converts abstract EA Skills into Claude-specific tool definitions.

    Claude uses the following tool schema:
    {
        "name": "skill_name",
        "description": "What the skill does",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
    """

    @staticmethod
    def convert_skill(skill: EASkill) -> Dict[str, Any]:
        """
        Convert EA Skill to Claude tool format.

        Args:
            skill: EA Skill instance

        Returns:
            Claude tool definition

        Example output:
        {
            "name": "generate_project_synthesis",
            "description": "Generate comprehensive project synthesis...",
            "input_schema": {
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
        """
        # Get JSON schema from Pydantic model
        pydantic_schema = skill.input_schema.model_json_schema()

        # Extract properties and required fields
        properties = pydantic_schema.get("properties", {})
        required = pydantic_schema.get("required", [])

        # Clean up properties (remove $defs if present)
        cleaned_properties = {}
        for prop_name, prop_schema in properties.items():
            # Remove internal Pydantic fields
            cleaned_prop = {
                k: v for k, v in prop_schema.items()
                if k not in ["title", "default"]
            }

            # Handle enums
            if "enum" in prop_schema:
                cleaned_prop["enum"] = prop_schema["enum"]

            # Ensure description is present
            if "description" not in cleaned_prop:
                cleaned_prop["description"] = f"Parameter: {prop_name}"

            cleaned_properties[prop_name] = cleaned_prop

        # Build Claude-specific tool schema
        claude_tool = {
            "name": skill.name,
            "description": skill.description,
            "input_schema": {
                "type": "object",
                "properties": cleaned_properties,
                "required": required
            }
        }

        logger.debug(f"Converted skill '{skill.name}' for Claude")
        return claude_tool

    @staticmethod
    def convert_skills(skills: List[EASkill]) -> List[Dict[str, Any]]:
        """
        Convert multiple skills.

        Args:
            skills: List of EA Skills

        Returns:
            List of Claude tool definitions
        """
        return [ClaudeAdapter.convert_skill(skill) for skill in skills]

    @staticmethod
    def parse_tool_use(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Claude's tool use response.

        Args:
            response: Claude API response

        Returns:
            Parsed tool call information

        Example Claude response content block:
        {
            "type": "tool_use",
            "id": "toolu_01A09q90qw90lq917835lq9",
            "name": "generate_project_synthesis",
            "input": {
                "project_name": "AI_Assistant",
                "output_format": "markdown"
            }
        }
        """
        # Extract tool use from Claude response
        content = response.get("content", [])

        tool_calls = []
        for block in content:
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {})
                })

        return {
            "has_tool_calls": len(tool_calls) > 0,
            "tool_calls": tool_calls
        }

    @staticmethod
    def format_tool_result(tool_call_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format tool execution result for Claude.

        Args:
            tool_call_id: ID of the tool call being responded to
            result: Result from skill execution

        Returns:
            Formatted tool result for Claude
        """
        import json

        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": json.dumps(result)
        }
