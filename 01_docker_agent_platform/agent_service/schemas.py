"""Pydantic models for the agent service."""
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    task_id: str
    query: str = Field(..., min_length=3, max_length=2000)


class AgentRunResponse(BaseModel):
    summary: str
    analysis: str
    recommendations: list[str]
    keywords: list[str]
    retrieved_knowledge: list[str]
