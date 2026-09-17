"""Deterministic API tests. No Docker required to run these."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Build a TestClient against an isolated, per-test data file.

    Each test gets its own JSON file under pytest's tmp_path so tests never
    share state and can run in any order.
    """
    data_file = tmp_path / "items.json"
    monkeypatch.setenv("DATA_FILE", str(data_file))
    monkeypatch.setenv("ENVIRONMENT", "test")

    import app.config as config_module
    import app.main as main_module

    config_module.get_settings.cache_clear()
    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "app_name" in body
    assert body["environment"] == "test"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_item(client):
    response = client.post("/items", json={"name": "Widget", "description": "A test widget"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Widget"
    assert body["description"] == "A test widget"
    assert "id" in body
    assert "created_at" in body


def test_create_item_validation_failure(client):
    response = client.post("/items", json={"name": ""})
    assert response.status_code == 422


def test_list_items(client):
    client.post("/items", json={"name": "First"})
    client.post("/items", json={"name": "Second"})

    response = client.get("/items")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {"First", "Second"}


def test_get_item_by_id(client):
    created = client.post("/items", json={"name": "Gizmo"}).json()

    response = client.get(f"/items/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_item_not_found(client):
    response = client.get("/items/does-not-exist")
    assert response.status_code == 404


def test_delete_item(client):
    created = client.post("/items", json={"name": "ToDelete"}).json()

    delete_response = client.delete(f"/items/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/items/{created['id']}")
    assert get_response.status_code == 404


def test_delete_item_not_found(client):
    response = client.delete("/items/does-not-exist")
    assert response.status_code == 404


def test_items_persist_across_store_instances(client, tmp_path):
    """Items written to disk should survive re-reading the JSON file."""
    created = client.post("/items", json={"name": "Persisted"}).json()

    from app.storage import ItemStore

    import os

    data_file = os.environ["DATA_FILE"]
    fresh_store = ItemStore(data_file)
    fetched = fresh_store.get_item(created["id"])
    assert fetched is not None
    assert fetched.name == "Persisted"
