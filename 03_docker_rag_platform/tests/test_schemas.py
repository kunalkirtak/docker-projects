"""
Unit tests for request validation (app/schemas.py).

These test Pydantic validation logic only — no database or network
access is required, so they are safe to run anywhere, including
Google Colab.
"""

import pytest
from pydantic import ValidationError

from app.schemas import DocumentCreate, SearchRequest


def test_document_create_accepts_valid_payload():
    doc = DocumentCreate(title="Docker Basics", content="Docker packages apps into containers.")
    assert doc.title == "Docker Basics"


def test_document_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        DocumentCreate(title="", content="some content")


def test_document_create_rejects_empty_content():
    with pytest.raises(ValidationError):
        DocumentCreate(title="Title", content="")


def test_search_request_default_limit():
    req = SearchRequest(query="docker networking")
    assert req.limit == 5


def test_search_request_rejects_zero_limit():
    with pytest.raises(ValidationError):
        SearchRequest(query="docker networking", limit=0)


def test_search_request_rejects_oversized_limit():
    with pytest.raises(ValidationError):
        SearchRequest(query="docker networking", limit=1000)
