"""Task management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from core.database import get_db
from core.models import Task
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskCreate(BaseModel):
    """Task creation request."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None


class TaskUpdate(BaseModel):
    """Task update request."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    """Task response."""
    id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    source_type: Optional[str]
    source_id: Optional[str]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    user_id: str = "default_user",  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """Create a new task."""
    try:
        db_task = Task(
            user_id=user_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            source_type=task.source_type,
            source_id=task.source_id
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """List tasks with optional status filter."""
    try:
        query = db.query(Task).filter(Task.user_id == user_id)
        
        if status:
            query = query.filter(Task.status == status)
        
        tasks = query.order_by(Task.created_at.desc()).all()
        return tasks
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Get a specific task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # Set completed_at if status changed to completed
        if task_update.status == "completed" and not task.completed_at:
            task.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(task)
        return task
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task")


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        db.delete(task)
        db.commit()
        return {"status": "deleted", "task_id": str(task_id)}
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete task")
