"""Skills API endpoints - Skill discovery, registration, and execution."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from backend.core.skills.base import SkillRegistry, SkillCategory
from backend.core.adapters import ClaudeAdapter, GeminiAdapter, OllamaAdapter

# Import skills
from backend.core.skills.weekly_review import GenerateWeeklyReviewSkill
from backend.core.skills.knowledge_search import SearchKnowledgeBaseSkill
from backend.core.skills.task_extraction import ExtractTasksSkill
from backend.core.skills.project_synthesis import GenerateProjectSynthesisSkill

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize skill registry
skill_registry = SkillRegistry()


class SkillExecutionRequest(BaseModel):
    """Request to execute a skill."""
    skill_name: str = Field(..., description="Name of the skill to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Skill parameters")
    user_id: Optional[str] = Field(None, description="User identifier")


class SkillListResponse(BaseModel):
    """Response listing available skills."""
    skills: List[Dict[str, Any]]
    total: int


class SkillDetailResponse(BaseModel):
    """Detailed information about a skill."""
    name: str
    description: str
    category: str
    input_schema: Dict[str, Any]
    compatibility: Dict[str, bool]


class ToolSchemaResponse(BaseModel):
    """Tool schemas for specific LLM provider."""
    provider: str
    tools: List[Dict[str, Any]]
    total: int


@router.on_event("startup")
async def register_skills():
    """Register all available skills on startup."""
    logger.info("Registering EA Skills...")

    skills = [
        GenerateWeeklyReviewSkill(),
        SearchKnowledgeBaseSkill(),
        ExtractTasksSkill(),
        GenerateProjectSynthesisSkill()
    ]

    for skill in skills:
        skill_registry.register(skill)

    logger.info(f"Registered {len(skills)} skills successfully")


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    llm_compatible: Optional[str] = Query(
        None,
        description="Filter by LLM compatibility: local, gemini, or claude"
    )
):
    """
    List all available skills with optional filters.

    This endpoint allows discovery of skills that can be used with the AI assistant.
    Skills can be filtered by category (automation, synthesis, etc.) or by
    LLM compatibility (local, gemini, claude).
    """
    # Get filtered skills
    skills = skill_registry.list_skills(
        category=category,
        llm_compatible=llm_compatible
    )

    # Format response
    skills_data = [
        {
            "name": skill.name,
            "description": skill.description,
            "category": skill.category.value,
            "compatibility": {
                "local": skill.supports_local,
                "gemini": skill.supports_gemini,
                "claude": skill.supports_claude
            }
        }
        for skill in skills
    ]

    return SkillListResponse(
        skills=skills_data,
        total=len(skills_data)
    )


@router.get("/skills/{skill_name}", response_model=SkillDetailResponse)
async def get_skill_details(skill_name: str):
    """
    Get detailed information about a specific skill.

    Returns the skill's description, category, input schema, and
    LLM compatibility information.
    """
    skill = skill_registry.get_skill(skill_name)

    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    return SkillDetailResponse(
        name=skill.name,
        description=skill.description,
        category=skill.category.value,
        input_schema=skill.to_json_schema(),
        compatibility={
            "local": skill.supports_local,
            "gemini": skill.supports_gemini,
            "claude": skill.supports_claude
        }
    )


@router.post("/skills/execute")
async def execute_skill(request: SkillExecutionRequest):
    """
    Execute a skill with provided parameters.

    This endpoint allows direct execution of skills for testing or
    manual invocation. In production, skills are typically invoked
    by the orchestrator agent.
    """
    logger.info(f"Executing skill: {request.skill_name}")

    try:
        result = await skill_registry.execute_skill(
            skill_name=request.skill_name,
            **request.parameters
        )

        return {
            "success": True,
            "skill_name": request.skill_name,
            "result": result
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Skill execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Skill execution failed: {str(e)}"
        )


@router.get("/skills/tools/{provider}", response_model=ToolSchemaResponse)
async def get_tools_for_provider(
    provider: str = Query(
        ...,
        description="LLM provider: claude, gemini, or ollama"
    )
):
    """
    Get tool schemas for a specific LLM provider.

    This endpoint converts all registered skills into the tool/function
    calling format required by the specified LLM provider. This enables
    the LLM to understand what skills are available and how to invoke them.

    Supported providers:
    - claude: Anthropic Claude tool format
    - gemini: Google Gemini function declarations
    - ollama: Ollama tool format (OpenAI-compatible)
    """
    provider = provider.lower()

    # Get all skills
    all_skills = skill_registry.list_skills()

    # Filter skills by provider compatibility
    if provider == "claude":
        compatible_skills = [s for s in all_skills if s.supports_claude]
        adapter = ClaudeAdapter()
        tools = adapter.convert_skills(compatible_skills)

    elif provider == "gemini":
        compatible_skills = [s for s in all_skills if s.supports_gemini]
        adapter = GeminiAdapter()
        tools = adapter.convert_skills(compatible_skills)

    elif provider == "ollama":
        compatible_skills = [s for s in all_skills if s.supports_local]
        adapter = OllamaAdapter()
        tools = adapter.convert_skills(compatible_skills)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Must be one of: claude, gemini, ollama"
        )

    return ToolSchemaResponse(
        provider=provider,
        tools=tools,
        total=len(tools)
    )


@router.get("/skills/categories")
async def list_skill_categories():
    """
    List all available skill categories.

    Returns a list of skill categories that can be used to filter skills.
    """
    categories = [
        {
            "value": cat.value,
            "name": cat.value.title(),
            "description": _get_category_description(cat)
        }
        for cat in SkillCategory
    ]

    return {
        "categories": categories,
        "total": len(categories)
    }


def _get_category_description(category: SkillCategory) -> str:
    """Get human-readable description for skill category."""
    descriptions = {
        SkillCategory.AUTOMATION: "Skills that automate repetitive tasks and workflows",
        SkillCategory.SYNTHESIS: "Skills that synthesize and summarize information",
        SkillCategory.RETRIEVAL: "Skills that search and retrieve information",
        SkillCategory.COMMUNICATION: "Skills that send messages and notifications",
        SkillCategory.ANALYSIS: "Skills that analyze data and extract insights"
    }
    return descriptions.get(category, "")


@router.get("/skills/stats")
async def get_skill_statistics():
    """
    Get statistics about registered skills.

    Returns counts by category, LLM compatibility, and total skills.
    """
    all_skills = skill_registry.list_skills()

    # Count by category
    category_counts = {}
    for cat in SkillCategory:
        count = len([s for s in all_skills if s.category == cat])
        category_counts[cat.value] = count

    # Count by LLM compatibility
    llm_counts = {
        "local": len([s for s in all_skills if s.supports_local]),
        "gemini": len([s for s in all_skills if s.supports_gemini]),
        "claude": len([s for s in all_skills if s.supports_claude])
    }

    return {
        "total_skills": len(all_skills),
        "by_category": category_counts,
        "by_llm": llm_counts
    }
