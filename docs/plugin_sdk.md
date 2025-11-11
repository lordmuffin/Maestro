# Maestro Plugin SDK Guide

## Introduction

The Maestro Plugin SDK enables developers to create custom EA (Executive Assistant) Skills that seamlessly integrate with the Maestro AI platform. Skills are LLM-agnostic and work across Local, Gemini, and Claude workers.

## Quick Start

### 1. Install Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/maestro.git
cd maestro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Create Your First Skill

Create a new file `my_skill.py`:

```python
"""My Custom Skill - Does something awesome."""
from typing import Dict, Any
from pydantic import BaseModel, Field

from backend.core.skills.base import EASkill, SkillCategory


class MySkillInput(BaseModel):
    """Input schema for My Custom Skill."""

    input_text: str = Field(
        ...,
        description="The text to process",
        min_length=1,
        max_length=1000
    )
    option: str = Field(
        default="default",
        description="Processing option: default, advanced, or custom"
    )


class MyCustomSkill(EASkill):
    """
    My Custom Skill does something amazing.

    Detailed description of what your skill does, when to use it,
    and what it returns. This description helps the LLM understand
    when and how to invoke your skill.
    """

    name = "my_custom_skill"
    description = "Short one-line description for LLM"
    category = SkillCategory.AUTOMATION
    input_schema = MySkillInput

    # Set LLM compatibility
    supports_local = True
    supports_gemini = True
    supports_claude = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the skill.

        Args:
            **kwargs: Validated skill parameters

        Returns:
            Dictionary with execution results
        """
        # Validate inputs (raises ValidationError if invalid)
        validated = self.validate_parameters(**kwargs)

        # Your skill logic here
        result_text = f"Processed: {validated.input_text}"

        # Return structured response
        return {
            "success": True,
            "result": result_text,
            "option_used": validated.option
        }
```

### 3. Register Your Skill

Edit `backend/api/routes/skills.py`:

```python
# Add import
from my_skill import MyCustomSkill

# In register_skills() function:
@router.on_event("startup")
async def register_skills():
    """Register all available skills on startup."""
    logger.info("Registering EA Skills...")

    skills = [
        # ... existing skills ...
        MyCustomSkill()  # Add your skill
    ]

    for skill in skills:
        skill_registry.register(skill)
```

### 4. Test Your Skill

Create `test_my_skill.py`:

```python
"""Tests for MyCustomSkill."""
import pytest
from my_skill import MyCustomSkill


class TestMyCustomSkill:
    """Tests for MyCustomSkill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test basic execution."""
        skill = MyCustomSkill()
        result = await skill.execute(
            input_text="test input",
            option="default"
        )

        assert result["success"] is True
        assert "Processed: test input" in result["result"]

    @pytest.mark.asyncio
    async def test_validation_error(self):
        """Test validation with invalid input."""
        from pydantic import ValidationError

        skill = MyCustomSkill()

        with pytest.raises(ValidationError):
            skill.validate_parameters(
                input_text=""  # Too short (min_length=1)
            )
```

Run tests:

```bash
pytest test_my_skill.py -v
```

### 5. Use Your Skill

Via API:

```bash
curl -X POST http://localhost:8000/api/v1/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "my_custom_skill",
    "parameters": {
      "input_text": "Hello, Maestro!",
      "option": "advanced"
    }
  }'
```

Via Open WebUI:

```
/skill my_custom_skill {"input_text": "Hello, Maestro!", "option": "advanced"}
```

## Skill Development Guide

### Input Schema Best Practices

Use Pydantic's rich validation features:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum


class Priority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AdvancedSkillInput(BaseModel):
    """Advanced input schema with validation."""

    # Required string with constraints
    title: str = Field(
        ...,
        description="Title of the item",
        min_length=3,
        max_length=100
    )

    # Optional field with default
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Priority level"
    )

    # List field
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags",
        max_items=10
    )

    # Numeric constraints
    count: int = Field(
        default=1,
        description="Number of items",
        ge=1,  # Greater than or equal to 1
        le=100  # Less than or equal to 100
    )

    # Optional field
    notes: Optional[str] = Field(
        None,
        description="Additional notes"
    )

    # Custom validator
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
```

### Skill Categories

Choose the appropriate category:

```python
from backend.core.skills.base import SkillCategory

# AUTOMATION: Tasks that automate workflows
# Examples: Send email, update spreadsheet, create calendar event
category = SkillCategory.AUTOMATION

# SYNTHESIS: Skills that synthesize information
# Examples: Generate report, summarize documents
category = SkillCategory.SYNTHESIS

# RETRIEVAL: Skills that search/retrieve data
# Examples: Search vault, find documents, query database
category = SkillCategory.RETRIEVAL

# COMMUNICATION: Skills that send messages
# Examples: Send email, post to Slack, create notification
category = SkillCategory.COMMUNICATION

# ANALYSIS: Skills that analyze data
# Examples: Extract tasks, analyze sentiment, classify documents
category = SkillCategory.ANALYSIS
```

### LLM Compatibility

Set compatibility flags based on your skill's requirements:

```python
class MySkill(EASkill):
    # Privacy-sensitive: Only local
    supports_local = True
    supports_gemini = False
    supports_claude = False

    # OR: G-Suite integration: Gemini preferred
    supports_local = True
    supports_gemini = True  # Preferred
    supports_claude = False

    # OR: Long-context synthesis: Claude preferred
    supports_local = True
    supports_gemini = True
    supports_claude = True  # Preferred

    # OR: Universal: All LLMs
    supports_local = True
    supports_gemini = True
    supports_claude = True
```

### Async Execution

All skills must use async/await:

```python
import asyncio
import httpx


class AsyncSkill(EASkill):
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute with async operations."""
        validated = self.validate_parameters(**kwargs)

        # Async HTTP request
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/data")
            data = response.json()

        # Async database query
        # result = await db.query("SELECT ...")

        # Concurrent operations
        results = await asyncio.gather(
            self._operation1(),
            self._operation2(),
            self._operation3()
        )

        return {"success": True, "data": results}

    async def _operation1(self):
        """Helper async operation."""
        await asyncio.sleep(1)  # Simulated work
        return "result1"
```

### Error Handling

Always return structured responses:

```python
async def execute(self, **kwargs) -> Dict[str, Any]:
    """Execute with proper error handling."""
    try:
        validated = self.validate_parameters(**kwargs)

        # Your logic here
        result = self._do_work(validated)

        return {
            "success": True,
            "data": result,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "validation_error"
        }

    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Internal error occurred",
            "error_type": "execution_error"
        }
```

### Integration with Phase 1-3 Components

Access backend services in your skills:

```python
from backend.core.rag import ObsidianRAG
from backend.services.path_mapping import PathMappingService
from backend.integrations.google.drive_client import GoogleDriveClient


class IntegratedSkill(EASkill):
    """Skill that integrates with other components."""

    def __init__(self):
        super().__init__()
        # Initialize services
        self.rag = ObsidianRAG()
        self.drive_client = GoogleDriveClient()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute with backend integration."""
        validated = self.validate_parameters(**kwargs)

        # Use Local RAG (Phase 1)
        rag_result = self.rag.query(validated.query)

        # Use Cloud integration (Phase 2)
        files = self.drive_client.search_files(validated.query)

        return {
            "success": True,
            "local_results": rag_result,
            "cloud_results": files
        }
```

## Testing

### Unit Tests

```python
import pytest
from my_skill import MyCustomSkill


@pytest.mark.asyncio
async def test_successful_execution():
    """Test successful skill execution."""
    skill = MyCustomSkill()
    result = await skill.execute(
        input_text="test",
        option="default"
    )

    assert result["success"] is True
    assert "result" in result


@pytest.mark.asyncio
async def test_invalid_input():
    """Test with invalid input."""
    from pydantic import ValidationError

    skill = MyCustomSkill()

    with pytest.raises(ValidationError):
        skill.validate_parameters(
            input_text=""  # Invalid
        )


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases."""
    skill = MyCustomSkill()

    # Test with maximum length input
    result = await skill.execute(
        input_text="x" * 1000
    )
    assert result["success"] is True
```

### Integration Tests

```python
import pytest
from backend.core.skills.base import SkillRegistry


@pytest.mark.asyncio
async def test_skill_registration():
    """Test skill registration and execution."""
    registry = SkillRegistry()
    registry.clear()

    skill = MyCustomSkill()
    registry.register(skill)

    # Verify registration
    assert registry.get_skill(skill.name) is not None

    # Test execution through registry
    result = await registry.execute_skill(
        skill_name=skill.name,
        input_text="test"
    )

    assert result["success"] is True
```

## Publishing Your Skill

### 1. Documentation

Create a README for your skill:

```markdown
# My Custom Skill

## Description
Detailed description of what your skill does.

## Usage

### Parameters
- `input_text` (required): Description
- `option` (optional): Description

### Example

\`\`\`python
result = await skill.execute(
    input_text="Hello",
    option="default"
)
\`\`\`

## LLM Compatibility
- ✅ Local (Ollama)
- ✅ Gemini
- ✅ Claude

## License
MIT
```

### 2. Package Structure

```
my_skill/
├── __init__.py
├── my_skill.py
├── tests/
│   └── test_my_skill.py
├── README.md
├── requirements.txt
└── setup.py
```

### 3. Create Pull Request

1. Fork the Maestro repository
2. Create a feature branch: `git checkout -b skill/my-custom-skill`
3. Add your skill to `backend/core/skills/`
4. Add tests to `backend/tests/`
5. Update documentation
6. Submit PR with description

## Examples

See the `backend/core/skills/` directory for production examples:
- `weekly_review.py` - Synthesis skill
- `knowledge_search.py` - Retrieval skill
- `task_extraction.py` - Analysis skill
- `project_synthesis.py` - Synthesis skill

## Advanced Topics

### Streaming Responses

For long-running skills, implement streaming:

```python
async def execute_stream(self, **kwargs):
    """Execute with streaming response."""
    validated = self.validate_parameters(**kwargs)

    yield {"status": "starting", "progress": 0}

    for i in range(10):
        await asyncio.sleep(1)
        yield {"status": "processing", "progress": (i + 1) * 10}

    yield {"status": "complete", "result": "..."}
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache


class CachedSkill(EASkill):
    @lru_cache(maxsize=128)
    def _expensive_operation(self, key: str):
        """Cached expensive operation."""
        # Expensive computation
        return result

    async def execute(self, **kwargs) -> Dict[str, Any]:
        result = self._expensive_operation(kwargs["key"])
        return {"success": True, "data": result}
```

### Rate Limiting

Implement rate limiting for API calls:

```python
import time
from collections import deque


class RateLimitedSkill(EASkill):
    def __init__(self):
        super().__init__()
        self.call_times = deque(maxlen=100)  # Track last 100 calls

    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Check rate limit (max 100 calls per minute)
        now = time.time()
        if len(self.call_times) == 100:
            oldest = self.call_times[0]
            if now - oldest < 60:
                return {
                    "success": False,
                    "error": "Rate limit exceeded"
                }

        self.call_times.append(now)

        # Execute skill
        return {"success": True}
```

## Support

- **Documentation**: https://docs.maestro.ai
- **Issues**: https://github.com/yourusername/maestro/issues
- **Discussions**: https://github.com/yourusername/maestro/discussions
- **Discord**: https://discord.gg/maestro

## License

MIT License - See LICENSE file for details
