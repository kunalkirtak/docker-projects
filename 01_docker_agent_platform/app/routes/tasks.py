"""Task creation and retrieval endpoints."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.orchestration import AgentServiceError, run_agent_workflow
from app.schemas import AgentResult, TaskCreateRequest, TaskListResponse, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


def _new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreateRequest, db: Session = Depends(get_db)) -> TaskResponse:
    task_id = _new_task_id()
    logger.info("task received task_id=%s", task_id)

    task = Task(task_id=task_id, query=payload.query, status=TaskStatus.PROCESSING.value)
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        agent_response = run_agent_workflow(task_id=task_id, query=payload.query)
        result = AgentResult.model_validate(agent_response)
        task.status = TaskStatus.COMPLETED.value
        task.result = result.model_dump()
        task.error = None
        logger.info("task completed task_id=%s", task_id)
    except AgentServiceError as exc:
        task.status = TaskStatus.FAILED.value
        task.error = str(exc)
        logger.error("task failed task_id=%s error=%s", task_id, exc)

    db.add(task)
    db.commit()
    db.refresh(task)

    return _to_response(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskResponse:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    return _to_response(task)


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(get_db)) -> TaskListResponse:
    tasks = db.execute(select(Task).order_by(Task.created_at.desc())).scalars().all()
    return TaskListResponse(tasks=[_to_response(t) for t in tasks], count=len(tasks))


def _to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        status=TaskStatus(task.status),
        query=task.query,
        result=AgentResult.model_validate(task.result) if task.result else None,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
