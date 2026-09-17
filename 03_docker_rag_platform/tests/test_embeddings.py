"""
Unit tests for app/embeddings.py.

These are pure unit tests: they do not require PostgreSQL, Qdrant,
or any network access, so they run the same way in CI, in Colab, or
inside the API container. They do NOT test PostgreSQL or Qdrant
connectivity — see the README's "Testing" section for how to run a
full integration check against the live Docker Compose stack.
"""

import math

from app.embeddings import embed_text
from app.config import settings


def test_embedding_dimension_matches_settings():
    vector = embed_text("docker containers are useful")
    assert len(vector) == settings.embedding_dim


def test_embedding_dimension_is_overridable():
    vector = embed_text("docker containers are useful", dim=64)
    assert len(vector) == 64


def test_embedding_is_deterministic():
    text = "PostgreSQL and Qdrant run as separate containers"
    first = embed_text(text)
    second = embed_text(text)
    assert first == second


def test_embedding_is_normalized():
    vector = embed_text("semantic retrieval over a vector database")
    norm = math.sqrt(sum(component * component for component in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-6, abs_tol=1e-6)


def test_empty_text_returns_zero_vector():
    vector = embed_text("")
    assert vector == [0.0] * settings.embedding_dim
    assert all(component == 0.0 for component in vector)


def test_different_text_produces_different_vectors():
    vector_a = embed_text("containerized rag platform")
    vector_b = embed_text("completely unrelated sentence about cooking")
    assert vector_a != vector_b
