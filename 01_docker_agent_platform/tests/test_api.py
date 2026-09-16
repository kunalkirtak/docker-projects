"""Tests for the FastAPI API service.

These tests intentionally avoid triggering the app's startup lifespan
(which initializes the PostgreSQL schema), so they can run without Docker
or a live database. They cover request validation and endpoints that do
not require a database round-trip. End-to-end task creation against a
live PostgreSQL + agent service is an integration concern -- see the
README for how to exercise that path with `docker compose up`.
"""
from fastapi.testclient import TestClient

from app.main import app

# Deliberately NOT using "with TestClient(app) as client" so the startup
# lifespan (which calls init_db() against PostgreSQL) does not run.
# raise_server_exceptions=False lets us assert on the resulting status
# code (e.g. a 500 from an unreachable database) instead of the test
# process re-raising the underlying exception.
client = TestClient(app, raise_server_exceptions=False)


def test_root_endpoint_returns_service_info() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "service" in body
    assert body["docs"] == "/docs"


def test_health_endpoint_reports_status_even_when_dependencies_are_down() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "postgres" in body["dependencies"]
    assert "agent" in body["dependencies"]


def test_create_task_rejects_blank_query() -> None:
    response = client.post("/tasks", json={"query": "   "})
    assert response.status_code == 422


def test_create_task_rejects_too_short_query() -> None:
    response = client.post("/tasks", json={"query": "hi"})
    assert response.status_code == 422


def test_create_task_rejects_missing_query() -> None:
    response = client.post("/tasks", json={})
    assert response.status_code == 422


def test_get_missing_task_returns_404_or_db_error() -> None:
    # Without a live database this call cannot succeed, but it must fail
    # cleanly (never hang or crash the process). Acceptable outcomes here
    # are a clean 404 (if a DB happens to be reachable) or a 5xx from the
    # ORM surfacing a clear connection error -- not an unhandled crash.
    response = client.get("/tasks/task_does_not_exist")
    assert response.status_code in {404, 500}
