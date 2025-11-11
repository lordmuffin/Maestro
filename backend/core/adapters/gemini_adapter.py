"""Adapter for converting EA Skills to Gemini function calling format."""
from typing import List, Dict, Any
from backend.core.skills.base import EASkill
import logging

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """
    Adapter for Google Gemini function calling format.

    Converts abstract EA Skills into Gemini-specific function declarations.

    Gemini uses "function_declarations" with specific type mappings:
    - STRING, INTEGER, NUMBER, BOOLEAN, ARRAY, OBJECT (all caps)
    """

    @staticmethod
    def convert_skill(skill: EASkill) -> Dict[str, Any]:
        """
        Convert EA Skill to Gemini function format.

        Args:
            skill: EA Skill instance

        Returns:
            Gemini function declaration

        Example output:
        {
            "name": "generate_project_synthesis",
            "description": "Generate comprehensive project synthesis...",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "project_name": {
                        "type": "STRING",
                        "description": "The name of the project..."
                    },
                    ...
                },
                "required": ["project_name"]
            }
        }
        """
        # Get schema from Pydantic model
        pydantic_schema = skill.input_schema.model_json_schema()

        # Convert properties to Gemini format
        properties = {}
        for prop_name, prop_schema in pydantic_schema.get("properties", {}).items():
            prop_type = prop_schema.get("type", "string")

            gemini_prop = {
                "type": GeminiAdapter._map_type_to_gemini(prop_type),
                "description": prop_schema.get("description", f"Parameter: {prop_name}")
            }

            # Handle enums
            if "enum" in prop_schema:
                gemini_prop["enum"] = prop_schema["enum"]

            # Handle arrays
            if prop_type == "array":
                items = prop_schema.get("items", {})
                items_type = items.get("type", "string")
                gemini_prop["items"] = {
                    "type": GeminiAdapter._map_type_to_gemini(items_type)
                }

            properties[prop_name] = gemini_prop

        # Build Gemini function declaration
        gemini_function = {
            "name": skill.name,
            "description": skill.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": pydantic_schema.get("required", [])
            }
        }

        logger.debug(f"Converted skill '{skill.name}' for Gemini")
        return gemini_function

    @staticmethod
    def _map_type_to_gemini(json_type: str) -> str:
        """
        Map JSON Schema types to Gemini types.

        Args:
            json_type: JSON Schema type

        Returns:
            Gemini type (all caps)
        """
        type_map = {
            "string": "STRING",
            "integer": "INTEGER",
            "number": "NUMBER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT"
        }
        return type_map.get(json_type.lower(), "STRING")

    @staticmethod
    def convert_skills(skills: List[EASkill]) -> List[Dict[str, Any]]:
        """
        Convert multiple skills.

        Args:
            skills: List of EA Skills

        Returns:
            List of Gemini function declarations
        """
        return [GeminiAdapter.convert_skill(skill) for skill in skills]

    @staticmethod
    def parse_function_call(response: Any) -> Dict[str, Any]:
        """
        Parse Gemini's function call response.

        Args:
            response: Gemini API response

        Returns:
            Parsed function call information

        Example Gemini response structure:
        response.candidates[0].content.parts[0].function_call
        {
            "name": "generate_project_synthesis",
            "args": {
                "project_name": "AI_Assistant",
                "output_format": "markdown"
            }
        }
        """
        function_calls = []

        try:
            # Gemini response structure
            if hasattr(response, 'candidates'):
                for candidate in response.candidates:
                    if hasattr(candidate, 'content'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call'):
                                fc = part.function_call
                                function_calls.append({
                                    "name": fc.name,
                                    "args": dict(fc.args) if hasattr(fc, 'args') else {}
                                })
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")

        return {
            "has_function_calls": len(function_calls) > 0,
            "function_calls": function_calls
        }

    @staticmethod
    def format_function_response(
        function_name: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format function execution result for Gemini.

        Args:
            function_name: Name of the function that was called
            result: Result from skill execution

        Returns:
            Formatted function response for Gemini
        """
        import json

        return {
            "function_response": {
                "name": function_name,
                "response": {
                    "content": json.dumps(result)
                }
            }
        }
