"""Tests for EA Skills Framework."""
import pytest
from pydantic import ValidationError

from backend.core.skills.base import (
    SkillRegistry,
    SkillCategory
)
from backend.core.skills.weekly_review import GenerateWeeklyReviewSkill
from backend.core.skills.knowledge_search import SearchKnowledgeBaseSkill
from backend.core.skills.task_extraction import ExtractTasksSkill
from backend.core.skills.project_synthesis import GenerateProjectSynthesisSkill


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        reg = SkillRegistry()
        reg.clear()  # Clear any existing skills
        return reg

    def test_register_skill(self, registry):
        """Test registering a skill."""
        skill = SearchKnowledgeBaseSkill()
        registry.register(skill)

        assert skill.name in [s.name for s in registry.list_skills()]

    def test_get_skill(self, registry):
        """Test retrieving a skill by name."""
        skill = SearchKnowledgeBaseSkill()
        registry.register(skill)

        retrieved = registry.get_skill(skill.name)
        assert retrieved is not None
        assert retrieved.name == skill.name

    def test_list_skills(self, registry):
        """Test listing all skills."""
        skills = [
            SearchKnowledgeBaseSkill(),
            GenerateWeeklyReviewSkill(),
            ExtractTasksSkill()
        ]

        for skill in skills:
            registry.register(skill)

        all_skills = registry.list_skills()
        assert len(all_skills) == 3

    def test_list_skills_by_category(self, registry):
        """Test filtering skills by category."""
        skills = [
            SearchKnowledgeBaseSkill(),  # RETRIEVAL
            GenerateWeeklyReviewSkill(),  # SYNTHESIS
            ExtractTasksSkill()  # ANALYSIS
        ]

        for skill in skills:
            registry.register(skill)

        retrieval_skills = registry.list_skills(category=SkillCategory.RETRIEVAL)
        assert len(retrieval_skills) == 1
        assert retrieval_skills[0].category == SkillCategory.RETRIEVAL

    def test_list_skills_by_llm_compatibility(self, registry):
        """Test filtering skills by LLM compatibility."""
        skills = [
            SearchKnowledgeBaseSkill(),  # local only
            GenerateWeeklyReviewSkill()  # all LLMs
        ]

        for skill in skills:
            registry.register(skill)

        local_skills = registry.list_skills(llm_compatible="local")
        assert len(local_skills) == 2

        gemini_skills = registry.list_skills(llm_compatible="gemini")
        assert len(gemini_skills) == 1  # Only weekly review

    @pytest.mark.asyncio
    async def test_execute_skill(self, registry):
        """Test executing a skill through the registry."""
        skill = SearchKnowledgeBaseSkill()
        registry.register(skill)

        result = await registry.execute_skill(
            skill_name=skill.name,
            query="test query",
            max_results=3
        )

        assert result["success"] is True
        assert result["query"] == "test query"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, registry):
        """Test executing a skill that doesn't exist."""
        with pytest.raises(ValueError, match="Skill not found"):
            await registry.execute_skill(
                skill_name="nonexistent_skill",
                query="test"
            )


class TestWeeklyReviewSkill:
    """Tests for GenerateWeeklyReviewSkill."""

    @pytest.mark.asyncio
    async def test_execute_default_params(self):
        """Test executing with default parameters."""
        skill = GenerateWeeklyReviewSkill()
        result = await skill.execute()

        assert result["success"] is True
        assert "report" in result
        assert result["format"] == "markdown"

    @pytest.mark.asyncio
    async def test_execute_custom_params(self):
        """Test executing with custom parameters."""
        skill = GenerateWeeklyReviewSkill()
        result = await skill.execute(
            week_offset=1,
            include_sections=["meetings", "tasks"],
            output_format="json"
        )

        assert result["success"] is True
        assert result["format"] == "json"
        assert "meetings" in result["sections_included"]
        assert "tasks" in result["sections_included"]

    def test_validate_invalid_params(self):
        """Test parameter validation with invalid inputs."""
        skill = GenerateWeeklyReviewSkill()

        with pytest.raises(ValidationError):
            skill.validate_parameters(week_offset=-1)  # Negative offset

        with pytest.raises(ValidationError):
            skill.validate_parameters(week_offset=100)  # Too large


class TestKnowledgeSearchSkill:
    """Tests for SearchKnowledgeBaseSkill."""

    @pytest.mark.asyncio
    async def test_execute_simple_search(self):
        """Test executing a simple search."""
        skill = SearchKnowledgeBaseSkill()
        result = await skill.execute(query="test query")

        assert result["success"] is True
        assert result["query"] == "test query"
        assert "results" in result
        assert result["results_found"] >= 0

    @pytest.mark.asyncio
    async def test_execute_with_scope(self):
        """Test executing search with scope limitation."""
        skill = SearchKnowledgeBaseSkill()
        result = await skill.execute(
            query="test query",
            search_scope=["Projects/AI"],
            max_results=3
        )

        assert result["success"] is True
        assert result["max_results"] == 3
        assert "Projects/AI" in result["search_scope"]

    def test_llm_compatibility(self):
        """Test that this skill is local-only."""
        skill = SearchKnowledgeBaseSkill()

        assert skill.supports_local is True
        assert skill.supports_gemini is False
        assert skill.supports_claude is False


class TestTaskExtractionSkill:
    """Tests for ExtractTasksSkill."""

    @pytest.mark.asyncio
    async def test_execute_from_recent_notes(self):
        """Test extracting tasks from recent notes."""
        skill = ExtractTasksSkill()
        result = await skill.execute(lookback_days=7)

        assert result["success"] is True
        assert "tasks_extracted" in result
        assert isinstance(result["tasks_extracted"], list)

    @pytest.mark.asyncio
    async def test_execute_from_specific_file(self):
        """Test extracting tasks from a specific file."""
        skill = ExtractTasksSkill()
        result = await skill.execute(
            source_file="Projects/AI/tasks.md",
            auto_create_tasks=False
        )

        assert result["success"] is True
        assert result["source"] == "Projects/AI/tasks.md"
        assert result["auto_created"] is False

    @pytest.mark.asyncio
    async def test_auto_create_tasks(self):
        """Test automatic task creation."""
        skill = ExtractTasksSkill()
        result = await skill.execute(
            lookback_days=3,
            auto_create_tasks=True
        )

        assert result["success"] is True
        assert result["auto_created"] is True
        assert "created_task_ids" in result


class TestProjectSynthesisSkill:
    """Tests for GenerateProjectSynthesisSkill."""

    @pytest.mark.asyncio
    async def test_execute_simple_synthesis(self):
        """Test basic project synthesis."""
        skill = GenerateProjectSynthesisSkill()
        result = await skill.execute(project_name="AI_Assistant")

        assert result["success"] is True
        assert result["project_name"] == "AI_Assistant"
        assert "synthesis" in result
        assert result["output_format"] == "markdown"

    @pytest.mark.asyncio
    async def test_execute_with_timeline(self):
        """Test synthesis with timeline."""
        skill = GenerateProjectSynthesisSkill()
        result = await skill.execute(
            project_name="Project_Nexus",
            include_timeline=True,
            include_related=True
        )

        assert result["success"] is True
        assert result["metadata"]["timeline_entries"] > 0
        assert result["metadata"]["related_projects"] > 0

    @pytest.mark.asyncio
    async def test_execute_json_format(self):
        """Test synthesis in JSON format."""
        skill = GenerateProjectSynthesisSkill()
        result = await skill.execute(
            project_name="Test_Project",
            output_format="json"
        )

        assert result["success"] is True
        assert result["output_format"] == "json"

        # Should be valid JSON
        import json
        json.loads(result["synthesis"])

    def test_validate_missing_required_param(self):
        """Test that project_name is required."""
        skill = GenerateProjectSynthesisSkill()

        with pytest.raises(ValidationError):
            skill.validate_parameters()  # Missing project_name


class TestSkillSchemaGeneration:
    """Tests for JSON schema generation."""

    def test_to_json_schema(self):
        """Test converting skill to JSON schema."""
        skill = SearchKnowledgeBaseSkill()
        schema = skill.to_json_schema()

        assert schema["name"] == skill.name
        assert schema["description"] == skill.description
        assert "parameters" in schema
        assert "properties" in schema["parameters"]
        assert "required" in schema["parameters"]

    def test_schema_has_required_fields(self):
        """Test that schema includes required fields."""
        skill = SearchKnowledgeBaseSkill()
        schema = skill.to_json_schema()

        required = schema["parameters"]["required"]
        assert "query" in required

    def test_schema_has_property_descriptions(self):
        """Test that properties have descriptions."""
        skill = GenerateWeeklyReviewSkill()
        schema = skill.to_json_schema()

        properties = schema["parameters"]["properties"]
        for prop_name, prop_schema in properties.items():
            assert "description" in prop_schema, f"Property {prop_name} missing description"
