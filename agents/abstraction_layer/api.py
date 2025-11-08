"""
FastAPI wrapper for Skill Abstraction Layer
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

app = FastAPI(
    title="Skill Abstraction Layer API",
    description="LLM-agnostic skill definitions and execution service",
    version="1.0.0"
)

class SkillExecutionRequest(BaseModel):
    skill_name: str
    parameters: Dict[str, Any]
    llm_provider: Optional[str] = "claude"  # claude, openai, gemini

class SkillExecutionResponse(BaseModel):
    status: str
    result: Any
    skill_name: str
    llm_provider: str

class SkillListResponse(BaseModel):
    status: str
    skills: List[Dict[str, Any]]

# Global skill registry instance
_skill_registry = None

def get_skill_registry():
    """Lazy load the skill registry"""
    global _skill_registry
    if _skill_registry is None:
        try:
            from skill_abstraction_layer import SkillRegistry
            _skill_registry = SkillRegistry()
        except Exception as e:
            print(f"Error initializing skill registry: {e}")
            _skill_registry = None
    return _skill_registry

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Skill Abstraction Layer API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "skills"
    }

@app.get("/skills", response_model=SkillListResponse)
async def list_skills():
    """
    List all available skills
    """
    try:
        registry = get_skill_registry()
        if registry is None:
            raise HTTPException(status_code=503, detail="Skill registry not initialized")

        # Get all registered skills
        if hasattr(registry, 'list_skills'):
            skills = registry.list_skills()
        else:
            # Fallback with known skills
            skills = [
                {
                    "name": "GenerateProjectSynthesis",
                    "description": "Generate comprehensive project overview",
                    "parameters": ["project_name", "context"]
                },
                {
                    "name": "ScheduleCalendarEvent",
                    "description": "Schedule events in Google Calendar",
                    "parameters": ["title", "start_time", "end_time", "description"]
                },
                {
                    "name": "UpdateSpreadsheet",
                    "description": "Update Google Sheets spreadsheet",
                    "parameters": ["spreadsheet_id", "range", "values"]
                },
                {
                    "name": "SearchKnowledgeBase",
                    "description": "Semantic search in Obsidian vault",
                    "parameters": ["query", "top_k"]
                }
            ]

        return SkillListResponse(
            status="success",
            skills=skills
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute", response_model=SkillExecutionResponse)
async def execute_skill(request: SkillExecutionRequest):
    """
    Execute a skill with the specified LLM provider
    """
    try:
        registry = get_skill_registry()
        if registry is None:
            raise HTTPException(status_code=503, detail="Skill registry not initialized")

        # Execute the skill
        if hasattr(registry, 'execute_skill'):
            result = registry.execute_skill(
                skill_name=request.skill_name,
                parameters=request.parameters,
                llm_provider=request.llm_provider
            )
        else:
            # Fallback response
            result = {
                "message": f"Skill '{request.skill_name}' execution requested",
                "parameters": request.parameters,
                "provider": request.llm_provider
            }

        return SkillExecutionResponse(
            status="success",
            result=result,
            skill_name=request.skill_name,
            llm_provider=request.llm_provider
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/skills/{skill_name}")
async def get_skill_details(skill_name: str):
    """Get detailed information about a specific skill"""
    try:
        registry = get_skill_registry()
        if registry is None:
            raise HTTPException(status_code=503, detail="Skill registry not initialized")

        # Get skill details
        if hasattr(registry, 'get_skill'):
            skill = registry.get_skill(skill_name)
            if skill is None:
                raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
            return {
                "status": "success",
                "skill": skill
            }
        else:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/adapters")
async def list_adapters():
    """List all available LLM adapters"""
    return {
        "status": "success",
        "adapters": [
            {
                "name": "claude",
                "provider": "Anthropic",
                "status": "available" if os.getenv("ANTHROPIC_API_KEY") else "missing_key"
            },
            {
                "name": "openai",
                "provider": "OpenAI",
                "status": "available" if os.getenv("OPENAI_API_KEY") else "missing_key"
            },
            {
                "name": "gemini",
                "provider": "Google",
                "status": "available" if os.getenv("GOOGLE_API_KEY") else "missing_key"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
