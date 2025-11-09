"""
FastAPI wrapper for Supervisor Agent
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

app = FastAPI(
    title="Supervisor Agent API",
    description="Multi-LLM orchestration and task routing service",
    version="1.0.0"
)

class TaskRequest(BaseModel):
    query: str
    sensitivity: Optional[str] = "medium"  # low, medium, high
    task_type: Optional[str] = None  # synthesis, automation, retrieval
    llm_provider: Optional[str] = None  # local, claude, gemini, openai
    model_tier: Optional[str] = None  # fast, standard, premium

class TaskResponse(BaseModel):
    status: str
    result: Any
    agent_used: str
    execution_time: Optional[float] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    privacy_warning: Optional[str] = None

class TaskStatusRequest(BaseModel):
    task_id: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[str] = None

# Global supervisor instance
_supervisor = None

def get_supervisor():
    """Lazy load the supervisor agent"""
    global _supervisor
    if _supervisor is None:
        try:
            from supervisor_agent import SupervisorAgent

            # Get service URLs from environment
            local_rag_url = os.getenv("LOCAL_RAG_URL", "http://local-rag:8001")
            path_mapping_url = os.getenv("PATH_MAPPING_URL", "http://path-mapping:8002")
            skills_url = os.getenv("SKILLS_URL", "http://skills:8004")

            _supervisor = SupervisorAgent(
                local_rag_url=local_rag_url,
                path_mapping_url=path_mapping_url,
                skills_url=skills_url
            )
        except Exception as e:
            print(f"Error initializing supervisor: {e}")
            _supervisor = None
    return _supervisor

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Supervisor Agent API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "supervisor"
    }

@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    Execute a task with intelligent agent routing and optional LLM provider/model selection
    """
    try:
        import model_registry

        supervisor = get_supervisor()
        if supervisor is None:
            raise HTTPException(status_code=503, detail="Supervisor agent not initialized")

        # Determine provider and model
        provider = request.llm_provider
        tier = request.model_tier or model_registry.get_default_tier()
        sensitivity = request.sensitivity or "medium"

        # If provider specified, validate it
        if provider:
            is_available, error_msg = model_registry.check_provider_available(provider)
            if not is_available:
                raise HTTPException(status_code=400, detail=error_msg)

            # Get model for tier
            try:
                model = model_registry.get_model_for_tier(provider, tier)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            provider = None
            model = None

        # Check for privacy warnings
        should_warn, warning_msg = None, None
        if provider:
            should_warn, warning_msg = model_registry.check_privacy_warning(provider, sensitivity)

        # Execute the task
        import time
        start_time = time.time()

        if hasattr(supervisor, 'execute'):
            result = supervisor.execute(
                query=request.query,
                sensitivity=sensitivity,
                task_type=request.task_type,
                llm_provider=provider,
                model=model
            )
            agent_used = result.get("agent", "unknown") if isinstance(result, dict) else "unknown"
            # Extract provider/model from result if available
            provider_used = result.get("provider", provider)
            model_used = result.get("model", model)
        else:
            # Fallback response
            result = {
                "response": "Supervisor agent is running but not fully integrated",
                "query": request.query
            }
            agent_used = "supervisor"
            provider_used = provider
            model_used = model

        execution_time = time.time() - start_time

        return TaskResponse(
            status="success",
            result=result,
            agent_used=agent_used,
            execution_time=execution_time,
            provider_used=provider_used,
            model_used=model_used,
            privacy_warning=warning_msg if should_warn else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/status", response_model=TaskStatusResponse)
async def get_task_status(request: TaskStatusRequest):
    """
    Get the status of a running task
    """
    try:
        # This would be implemented with a task queue/tracking system
        return TaskStatusResponse(
            task_id=request.task_id,
            status="completed",
            progress="100%"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def list_agents():
    """List available agents and their status"""
    try:
        import httpx

        agents_status = {}

        # Check Local RAG
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{os.getenv('LOCAL_RAG_URL', 'http://local-rag:8001')}/health",
                    timeout=5.0
                )
                agents_status["local_rag"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            agents_status["local_rag"] = "unreachable"

        # Check Path Mapping
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{os.getenv('PATH_MAPPING_URL', 'http://path-mapping:8002')}/health",
                    timeout=5.0
                )
                agents_status["path_mapping"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            agents_status["path_mapping"] = "unreachable"

        # Check Skills
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{os.getenv('SKILLS_URL', 'http://skills:8004')}/health",
                    timeout=5.0
                )
                agents_status["skills"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            agents_status["skills"] = "unreachable"

        return {
            "status": "success",
            "agents": agents_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
