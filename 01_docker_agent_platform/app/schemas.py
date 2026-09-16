"""Pydantic request/response models for the API service."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreateRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value.strip()


class AgentResult(BaseModel):
    summary: str
    analysis: str
    recommendations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    retrieved_knowledge: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    query: str
    result: Optional[AgentResult] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    count: int


class HealthResponse(BaseModel):
    status: str
    service: str
    dependencies: dict[str, Any] = Field(default_factory=dict)
