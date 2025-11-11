"""
Custom Open WebUI Pipeline for Maestro AI Executive Assistant.

This pipeline connects the Open WebUI frontend to the Maestro backend,
enabling skill execution and multi-LLM orchestration through the UI.
"""
from typing import List, Dict, Any, Iterator, Optional
from pydantic import BaseModel, Field
import requests
import json
import logging

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Maestro Pipeline for Open WebUI.

    This integrates Maestro's orchestration logic into Open WebUI's
    pipeline system, enabling the UI to interact with the backend
    skills and LLM orchestration.
    """

    class Valves(BaseModel):
        """Pipeline configuration valves (user-configurable settings)."""

        MAESTRO_BACKEND_URL: str = Field(
            default="http://backend:8000",
            description="Maestro backend API URL"
        )
        ENABLE_SKILLS: bool = Field(
            default=True,
            description="Enable EA Skills execution"
        )
        DEFAULT_LLM_PROVIDER: str = Field(
            default="ollama",
            description="Default LLM provider: ollama, gemini, or claude"
        )
        SKILL_TIMEOUT: int = Field(
            default=60,
            description="Timeout for skill execution (seconds)"
        )
        ENABLE_LOGGING: bool = Field(
            default=True,
            description="Enable detailed logging"
        )

    def __init__(self):
        """Initialize pipeline."""
        self.valves = self.Valves()
        self.name = "Maestro AI Executive Assistant"
        self.id = "maestro_pipeline"

        # Cache for available skills
        self._skills_cache: Optional[List[Dict[str, Any]]] = None

    async def on_startup(self):
        """Called when pipeline starts."""
        if self.valves.ENABLE_LOGGING:
            logger.info("Maestro pipeline initialized")

        # Load available skills
        await self._load_skills()

    async def on_shutdown(self):
        """Called when pipeline stops."""
        if self.valves.ENABLE_LOGGING:
            logger.info("Maestro pipeline shutdown")

    async def _load_skills(self):
        """Load available skills from backend."""
        try:
            response = requests.get(
                f"{self.valves.MAESTRO_BACKEND_URL}/api/v1/skills/skills",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self._skills_cache = data.get("skills", [])
                if self.valves.ENABLE_LOGGING:
                    logger.info(f"Loaded {len(self._skills_cache)} skills")
            else:
                logger.warning(f"Failed to load skills: {response.status_code}")
                self._skills_cache = []

        except Exception as e:
            logger.error(f"Error loading skills: {e}")
            self._skills_cache = []

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[Dict[str, Any]],
        body: Dict[str, Any]
    ) -> Iterator[str]:
        """
        Process user message through Maestro pipeline.

        Args:
            user_message: User's message
            model_id: Model identifier
            messages: Conversation history
            body: Request body

        Yields:
            Response chunks
        """
        try:
            # Extract user info
            user_id = body.get("user", {}).get("id", "default_user")

            if self.valves.ENABLE_LOGGING:
                logger.info(f"Processing message from user {user_id}: {user_message[:100]}")

            # Check if message is a skill invocation
            skill_result = self._try_skill_execution(user_message, user_id)

            if skill_result:
                # Skill was executed successfully
                yield self._format_skill_response(skill_result)
            else:
                # Normal LLM conversation
                # Pass through to backend orchestrator
                yield from self._forward_to_orchestrator(
                    user_message=user_message,
                    messages=messages,
                    user_id=user_id,
                    model_id=model_id
                )

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            yield f"❌ Error processing request: {str(e)}"

    def _try_skill_execution(
        self,
        message: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Try to execute message as a skill command.

        Supports commands like:
        - /skill <skill_name> <params>
        - @skill <skill_name> <params>

        Args:
            message: User message
            user_id: User identifier

        Returns:
            Skill execution result or None
        """
        if not self.valves.ENABLE_SKILLS:
            return None

        # Check for skill command prefix
        if not (message.startswith("/skill ") or message.startswith("@skill ")):
            return None

        try:
            # Parse skill command
            parts = message.split(" ", 2)
            if len(parts) < 2:
                return {"error": "Invalid skill command format"}

            skill_name = parts[1]

            # Parse parameters (simple JSON)
            params = {}
            if len(parts) > 2:
                try:
                    params = json.loads(parts[2])
                except json.JSONDecodeError:
                    # Try key=value format
                    params = self._parse_key_value_params(parts[2])

            # Execute skill via API
            response = requests.post(
                f"{self.valves.MAESTRO_BACKEND_URL}/api/v1/skills/execute",
                json={
                    "skill_name": skill_name,
                    "parameters": params,
                    "user_id": user_id
                },
                timeout=self.valves.SKILL_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Skill execution failed: {response.text}"}

        except Exception as e:
            logger.error(f"Skill execution error: {e}")
            return {"error": str(e)}

    def _parse_key_value_params(self, param_str: str) -> Dict[str, Any]:
        """Parse key=value parameter format."""
        params = {}
        for pair in param_str.split():
            if "=" in pair:
                key, value = pair.split("=", 1)
                # Try to parse as JSON value
                try:
                    params[key] = json.loads(value)
                except:
                    params[key] = value
        return params

    def _format_skill_response(self, skill_result: Dict[str, Any]) -> str:
        """Format skill execution result for display."""
        if "error" in skill_result:
            return f"❌ **Skill Error**: {skill_result['error']}"

        if not skill_result.get("success"):
            return "❌ Skill execution failed"

        # Format successful result
        result_data = skill_result.get("result", {})

        output = "✅ **Skill Executed Successfully**\n\n"
        output += f"**Skill**: `{skill_result.get('skill_name')}`\n\n"

        # Format result based on type
        if "report" in result_data:
            output += "## Result\n\n"
            output += result_data["report"]
        elif "synthesis" in result_data:
            output += "## Synthesis\n\n"
            output += result_data["synthesis"]
        elif "results" in result_data:
            output += "## Results\n\n"
            results = result_data["results"]
            if isinstance(results, list):
                for i, item in enumerate(results, 1):
                    output += f"{i}. {item}\n"
            else:
                output += str(results)
        else:
            # Generic result formatting
            output += "## Result\n\n"
            output += f"```json\n{json.dumps(result_data, indent=2)}\n```"

        return output

    def _forward_to_orchestrator(
        self,
        user_message: str,
        messages: List[Dict[str, Any]],
        user_id: str,
        model_id: str
    ) -> Iterator[str]:
        """
        Forward conversation to backend orchestrator.

        In a full implementation, this would integrate with the
        LangGraph supervisor agent from Phase 3.

        For now, we'll provide a simple pass-through to the LLM.
        """
        # Build context
        context = {
            "conversation_history": messages[-5:],  # Last 5 messages
            "model_id": model_id,
            "user_id": user_id
        }

        # Check if orchestrator endpoint exists
        try:
            response = requests.post(
                f"{self.valves.MAESTRO_BACKEND_URL}/api/v1/orchestrate/query",
                json={
                    "query": user_message,
                    "user_id": user_id,
                    "context": context
                },
                timeout=60,
                stream=True
            )

            if response.status_code == 200:
                # Stream response
                for line in response.iter_lines():
                    if line:
                        yield line.decode('utf-8') + "\n"
            else:
                # Fallback to simple response
                yield self._generate_fallback_response(user_message)

        except requests.exceptions.RequestException:
            # Orchestrator not available, use fallback
            yield self._generate_fallback_response(user_message)

    def _generate_fallback_response(self, user_message: str) -> str:
        """Generate fallback response when orchestrator is unavailable."""
        return f"""I'm Maestro, your AI Executive Assistant!

I have access to the following skills:
{self._format_skills_list()}

To execute a skill, use: `/skill <skill_name> <params>`

Example:
```
/skill search_knowledge_base {{"query": "project updates"}}
```

Your message: "{user_message}"

(Note: Full orchestration is coming soon in Phase 3!)
"""

    def _format_skills_list(self) -> str:
        """Format available skills as a list."""
        if not self._skills_cache:
            return "- (Loading skills...)"

        output = ""
        for skill in self._skills_cache[:5]:  # Show first 5
            output += f"- **{skill['name']}**: {skill['description'][:80]}...\n"

        if len(self._skills_cache) > 5:
            output += f"\n_...and {len(self._skills_cache) - 5} more_"

        return output


# Pipeline validation
def validate_pipeline():
    """Validate pipeline configuration."""
    pipeline = Pipeline()
    assert pipeline.name == "Maestro AI Executive Assistant"
    assert pipeline.id == "maestro_pipeline"
    print("✅ Pipeline validation passed")


if __name__ == "__main__":
    validate_pipeline()
