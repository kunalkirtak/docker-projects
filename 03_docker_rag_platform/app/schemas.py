"""Pydantic schemas used for request validation and response shaping."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=50)


class SearchResultItem(BaseModel):
    document_id: int
    title: str
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


class ContextRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=3, ge=1, le=20)


class ContextItem(BaseModel):
    document_id: int
    title: str
    content: str
    score: float


class ContextResponse(BaseModel):
    query: str
    context: List[ContextItem]


class HealthResponse(BaseModel):
    status: str
    database: str
    vector_store: str
