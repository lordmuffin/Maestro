"""
FastAPI wrapper for Maestro Evaluation Service
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Maestro Evaluation API",
    description="LLM Evaluation and Scorecard Service",
    version="1.0.0"
)

class EvaluationRequest(BaseModel):
    prompt: str
    num_runs: Optional[int] = 1
    models: Optional[List[str]] = ["claude", "gemini"]

class EvaluationResponse(BaseModel):
    status: str
    results: Dict[str, Any]
    message: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Maestro Evaluation API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "evaluation-api"
    }

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """
    Run LLM evaluation
    """
    try:
        # Import scorecard here to avoid loading during health checks
        import scorecard

        # Run evaluation (this would need to be adapted based on scorecard.py structure)
        results = {
            "prompt": request.prompt,
            "num_runs": request.num_runs,
            "models": request.models,
            "status": "completed",
            "message": "Evaluation service is running. Full integration requires scorecard.py adaptation."
        }

        return EvaluationResponse(
            status="success",
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Get evaluation metrics"""
    return {
        "status": "success",
        "metrics": {
            "total_evaluations": 0,
            "models_supported": ["claude", "gemini"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
