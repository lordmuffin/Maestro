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

class TaskResponse(BaseModel):
    status: str
    result: Any
    agent_used: str
    execution_time: Optional[float] = None

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
    Execute a task with intelligent agent routing
    """
    try:
        supervisor = get_supervisor()
        if supervisor is None:
            raise HTTPException(status_code=503, detail="Supervisor agent not initialized")

        # Execute the task
        import time
        start_time = time.time()

        if hasattr(supervisor, 'execute'):
            result = supervisor.execute(
                query=request.query,
                sensitivity=request.sensitivity,
                task_type=request.task_type
            )
            agent_used = result.get("agent", "unknown") if isinstance(result, dict) else "unknown"
        else:
            # Fallback response
            result = {
                "response": "Supervisor agent is running but not fully integrated",
                "query": request.query
            }
            agent_used = "supervisor"

        execution_time = time.time() - start_time

        return TaskResponse(
            status="success",
            result=result,
            agent_used=agent_used,
            execution_time=execution_time
        )
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
