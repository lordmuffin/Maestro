# Phase 4: Unified EA Skills Framework

## Overview

Phase 4 introduces the **Unified EA Skills Framework** - a platform-agnostic abstraction layer that enables "write once, run anywhere" skill definitions. Skills can be executed across different LLM providers (Local/Ollama, Google Gemini, Anthropic Claude) without modification.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   EA Skills Framework                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Abstract Skill Definitions                      │ │
│  │         (Pydantic BaseModel + ABC)                      │ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                          │
│         ┌──────────┴──────────┐                              │
│         │   Model Adapters    │                              │
│         ├─────────────────────┤                              │
│         │  • ClaudeAdapter    │                              │
│         │  • GeminiAdapter    │                              │
│         │  • OllamaAdapter    │                              │
│         └──────────┬──────────┘                              │
│                    │                                          │
│         ┌──────────┴──────────┐                              │
│         │   LLM Providers     │                              │
│         │  Tool/Function      │                              │
│         │  Calling APIs       │                              │
│         └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Abstract Skill Definition (`EASkill`)

All skills inherit from the `EASkill` base class:

```python
from backend.core.skills.base import EASkill, SkillCategory
from pydantic import BaseModel, Field
from typing import Dict, Any

class MySkillInput(BaseModel):
    """Input schema using Pydantic for validation."""
    param1: str = Field(..., description="Description for LLM")
    param2: int = Field(default=10, description="Optional parameter")

class MyCustomSkill(EASkill):
    """Your custom skill."""

    name = "my_custom_skill"
    description = "What this skill does"
    category = SkillCategory.AUTOMATION
    input_schema = MySkillInput

    # LLM compatibility flags
    supports_local = True
    supports_gemini = True
    supports_claude = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the skill logic."""
        validated = self.validate_parameters(**kwargs)

        # Your implementation here
        result = {"success": True, "data": "..."}

        return result
```

### 2. Model Adapters

Adapters convert abstract skills to LLM-specific formats:

#### Claude Adapter

```python
from backend.core.adapters import ClaudeAdapter

skill = MyCustomSkill()
adapter = ClaudeAdapter()
claude_tool = adapter.convert_skill(skill)

# Result: Claude tool definition
{
    "name": "my_custom_skill",
    "description": "What this skill does",
    "input_schema": {
        "type": "object",
        "properties": {...},
        "required": [...]
    }
}
```

#### Gemini Adapter

```python
from backend.core.adapters import GeminiAdapter

adapter = GeminiAdapter()
gemini_function = adapter.convert_skill(skill)

# Result: Gemini function declaration
{
    "name": "my_custom_skill",
    "description": "What this skill does",
    "parameters": {
        "type": "OBJECT",
        "properties": {...}
    }
}
```

#### Ollama Adapter

```python
from backend.core.adapters import OllamaAdapter

adapter = OllamaAdapter()
ollama_tool = adapter.convert_skill(skill)

# Result: OpenAI-compatible tool definition
{
    "type": "function",
    "function": {
        "name": "my_custom_skill",
        "description": "What this skill does",
        "parameters": {...}
    }
}
```

### 3. Skill Registry

Central registry for skill discovery and execution:

```python
from backend.core.skills.base import SkillRegistry

registry = SkillRegistry()

# Register skill
skill = MyCustomSkill()
registry.register(skill)

# List all skills
all_skills = registry.list_skills()

# Filter by category
automation_skills = registry.list_skills(
    category=SkillCategory.AUTOMATION
)

# Filter by LLM compatibility
claude_skills = registry.list_skills(llm_compatible="claude")

# Execute skill
result = await registry.execute_skill(
    skill_name="my_custom_skill",
    param1="value1",
    param2=20
)
```

## Built-in Skills

### 1. Weekly Review (`generate_weekly_review`)

Generate comprehensive weekly summaries:

```python
await registry.execute_skill(
    skill_name="generate_weekly_review",
    week_offset=0,  # 0 = current week, 1 = last week
    include_sections=["meetings", "tasks", "emails", "notes"],
    output_format="markdown"
)
```

**Response:**
```json
{
    "success": true,
    "report": "# Weekly Review\n...",
    "format": "markdown",
    "date_range": {
        "start": "2025-01-06T00:00:00",
        "end": "2025-01-13T00:00:00"
    },
    "metadata": {
        "total_meetings": 5,
        "total_tasks": 12,
        "total_emails": 8,
        "total_notes": 15
    }
}
```

### 2. Knowledge Search (`search_knowledge_base`)

Semantic search across Obsidian vault:

```python
await registry.execute_skill(
    skill_name="search_knowledge_base",
    query="project updates from last month",
    search_scope=["Projects", "Meetings"],  # Optional
    result_format="detailed",  # summary, detailed, or raw
    max_results=10
)
```

**Response:**
```json
{
    "success": true,
    "query": "project updates from last month",
    "results_found": 10,
    "results": [
        {
            "title": "Project Status Update",
            "file_path": "Projects/AI/Status.md",
            "relevance": "95%",
            "excerpt": "...",
            "tags": ["#project", "#status"],
            "modified": "2025-01-10"
        }
    ]
}
```

### 3. Task Extraction (`extract_tasks`)

Extract actionable tasks from notes:

```python
await registry.execute_skill(
    skill_name="extract_tasks",
    source_file="Meetings/2025-01-10.md",  # Optional
    lookback_days=7,  # If source_file not specified
    priority_threshold="medium",
    auto_create_tasks=false
)
```

**Response:**
```json
{
    "success": true,
    "tasks_found": 5,
    "tasks_extracted": [
        {
            "text": "Review PR #123",
            "priority": "high",
            "source": "Meetings/2025-01-10.md",
            "line_number": 15,
            "due_date": "2025-01-15",
            "context": "Code review needed"
        }
    ],
    "auto_created": false
}
```

### 4. Project Synthesis (`generate_project_synthesis`)

Generate comprehensive project overviews:

```python
await registry.execute_skill(
    skill_name="generate_project_synthesis",
    project_name="AI_Assistant",
    output_format="markdown",  # or json, html, executive_summary
    include_timeline=true,
    include_related=true
)
```

**Response:**
```json
{
    "success": true,
    "project_name": "AI_Assistant",
    "synthesis": "# AI_Assistant - Project Synthesis\n...",
    "output_format": "markdown",
    "metadata": {
        "documents_analyzed": 12,
        "timeline_entries": 8,
        "related_projects": 3,
        "word_count": 1250
    }
}
```

## API Endpoints

### List Skills

```http
GET /api/v1/skills/skills
GET /api/v1/skills/skills?category=automation
GET /api/v1/skills/skills?llm_compatible=claude
```

### Get Skill Details

```http
GET /api/v1/skills/skills/{skill_name}
```

### Execute Skill

```http
POST /api/v1/skills/execute
Content-Type: application/json

{
    "skill_name": "search_knowledge_base",
    "parameters": {
        "query": "test query",
        "max_results": 5
    },
    "user_id": "user123"
}
```

### Get Tools for LLM Provider

```http
GET /api/v1/skills/tools/claude
GET /api/v1/skills/tools/gemini
GET /api/v1/skills/tools/ollama
```

Returns tool/function schemas formatted for the specified LLM provider.

### Get Skill Statistics

```http
GET /api/v1/skills/stats
```

## Open WebUI Integration

Skills can be invoked through Open WebUI using the custom Maestro pipeline:

```
/skill search_knowledge_base {"query": "project updates", "max_results": 5}
```

or

```
@skill generate_weekly_review {"week_offset": 1, "output_format": "markdown"}
```

## Creating Custom Skills

See [Plugin SDK Guide](./plugin_sdk.md) for detailed instructions on creating and publishing custom skills.

## Best Practices

1. **Clear Descriptions**: Write detailed descriptions for both the skill and each parameter. These guide the LLM in understanding when and how to use the skill.

2. **Validation**: Use Pydantic's validation features (min_length, ge, le, enum) to ensure robust input validation.

3. **LLM Compatibility**: Set appropriate `supports_*` flags based on your skill's requirements:
   - `supports_local = True`: For privacy-sensitive operations
   - `supports_gemini = True`: For G-Suite integrations
   - `supports_claude = True`: For long-context synthesis

4. **Error Handling**: Always return structured responses with a `success` field:
   ```python
   return {
       "success": True/False,
       "error": "...",  # If success = False
       "data": {...}     # If success = True
   }
   ```

5. **Async/Await**: All skill `execute()` methods should be async to support long-running operations.

6. **Testing**: Write comprehensive tests for your skills (see `backend/tests/test_skills.py`).

## Security Considerations

1. **Input Validation**: All inputs are validated via Pydantic before execution.

2. **Privacy**: Skills marked `supports_local = True` can run entirely on local infrastructure.

3. **HITL (Human-in-the-Loop)**: Critical operations should require user confirmation (coming in orchestrator integration).

4. **Audit Logging**: All skill executions are logged for security and debugging.

## Performance

- **Lazy Loading**: Skills are only loaded when needed.
- **Caching**: Skill schemas are cached after first generation.
- **Async Execution**: All skills support concurrent execution.
- **Timeouts**: Skills should implement reasonable timeouts for long-running operations.

## Troubleshooting

### Skill Not Found

```
ValueError: Skill not found: my_skill
```

**Solution**: Ensure the skill is registered in the registry. Check `backend/api/routes/skills.py` startup event.

### Validation Error

```
ValidationError: 1 validation error for MySkillInput
```

**Solution**: Check that all required parameters are provided and match the expected types.

### LLM Incompatibility

```
Skill does not support provider: gemini
```

**Solution**: Check the skill's `supports_*` flags and use a compatible LLM provider.

## Next Steps

- [Plugin SDK Guide](./plugin_sdk.md) - Create custom skills
- [API Reference](./api_reference.md) - Detailed API documentation
- [Examples](./examples/) - Example skill implementations
