"""
Base classes for Unified EA Skills Framework.

This abstraction layer enables LLM-agnostic skill definitions
that work across Local/Gemini/Claude workers.
"""
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """Skill categories."""
    AUTOMATION = "automation"
    SYNTHESIS = "synthesis"
    RETRIEVAL = "retrieval"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"


class ParameterType(str, Enum):
    """Parameter data types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class SkillParameter(BaseModel):
    """Skill parameter definition."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class EASkill(ABC):
    """
    Abstract base class for Executive Assistant Skills.

    All skills must inherit from this class and implement execute().
    This enables the "write once, run anywhere" pattern across LLMs.
    """

    # Metadata (to be set by subclasses)
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.RETRIEVAL
    input_schema: Type[BaseModel]

    # LLM compatibility flags
    supports_local: bool = True
    supports_gemini: bool = True
    supports_claude: bool = True

    def __init__(self):
        """Initialize skill."""
        if not self.name:
            raise ValueError(f"Skill {self.__class__.__name__} must define 'name' attribute")
        if not self.description:
            raise ValueError(f"Skill {self.__class__.__name__} must define 'description' attribute")
        if not hasattr(self, 'input_schema'):
            raise ValueError(f"Skill {self.__class__.__name__} must define 'input_schema' attribute")

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the skill.

        Args:
            **kwargs: Skill parameters

        Returns:
            Execution result dictionary
        """
        pass

    def to_json_schema(self) -> Dict[str, Any]:
        """
        Convert skill to JSON Schema format.

        Used by adapters to generate LLM-specific tool definitions.

        Returns:
            JSON Schema dictionary
        """
        # Get schema from Pydantic model
        pydantic_schema = self.input_schema.model_json_schema()

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": pydantic_schema.get("properties", {}),
                "required": pydantic_schema.get("required", [])
            }
        }

    def validate_parameters(self, **kwargs) -> BaseModel:
        """
        Validate provided parameters.

        Args:
            **kwargs: Parameters to validate

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError if invalid
        """
        return self.input_schema(**kwargs)

    def __repr__(self) -> str:
        return f"<EASkill: {self.name}>"


class SkillRegistry:
    """
    Registry for all available EA Skills.

    Singleton that maintains the catalog of skills and
    provides discovery/execution capabilities.
    """

    _instance = None
    _skills: Dict[str, EASkill] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill: EASkill) -> None:
        """
        Register a skill.

        Args:
            skill: Skill instance to register
        """
        if skill.name in self._skills:
            logger.warning(f"Overwriting existing skill: {skill.name}")

        self._skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name}")

    def get_skill(self, name: str) -> Optional[EASkill]:
        """
        Get skill by name.

        Args:
            name: Skill name

        Returns:
            Skill instance or None
        """
        return self._skills.get(name)

    def list_skills(
        self,
        category: Optional[SkillCategory] = None,
        llm_compatible: Optional[str] = None
    ) -> List[EASkill]:
        """
        List registered skills with optional filters.

        Args:
            category: Filter by category
            llm_compatible: Filter by LLM compatibility ("local", "gemini", "claude")

        Returns:
            List of matching skills
        """
        skills = list(self._skills.values())

        if category:
            skills = [s for s in skills if s.category == category]

        if llm_compatible:
            if llm_compatible == "local":
                skills = [s for s in skills if s.supports_local]
            elif llm_compatible == "gemini":
                skills = [s for s in skills if s.supports_gemini]
            elif llm_compatible == "claude":
                skills = [s for s in skills if s.supports_claude]

        return skills

    def get_all_skills(self) -> Dict[str, EASkill]:
        """Get all registered skills."""
        return self._skills.copy()

    async def execute_skill(
        self,
        skill_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of skill to execute
            **kwargs: Skill parameters

        Returns:
            Execution result
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")

        # Validate parameters
        validated_input = skill.validate_parameters(**kwargs)

        # Execute skill
        return await skill.execute(**kwargs)

    def clear(self) -> None:
        """Clear all registered skills (useful for testing)."""
        self._skills.clear()
