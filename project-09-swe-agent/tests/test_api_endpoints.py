from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    async def fake_ensure():
        pass

    async def fake_close():
        pass

    import src.services.postgres_service as pg
    import src.api.main as api_main
    monkeypatch.setattr(pg, "ensure_schema", fake_ensure)
    monkeypatch.setattr(pg, "close_pool", fake_close)
    monkeypatch.setattr(api_main, "ensure_schema", fake_ensure)
    monkeypatch.setattr(api_main, "close_pool", fake_close)

    from src.api.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_task_not_found(client, monkeypatch):
    import src.api.routes.tasks as routes

    async def fake_get_task(task_id):
        return None

    monkeypatch.setattr(routes, "get_task", fake_get_task)
    response = client.get("/tasks/nonexistent-id")
    assert response.status_code == 404


def test_submit_task_returns_id(client, monkeypatch):
    import src.api.routes.tasks as routes

    async def fake_submit(issue_url):
        return "test-task-id-123"

    monkeypatch.setattr(routes, "submit_task", fake_submit)
    response = client.post("/tasks", json={"issue_url": "https://github.com/a/b/issues/1"})
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "test-task-id-123"


def test_approve_task_not_awaiting(client, monkeypatch):
    import src.api.routes.tasks as routes

    async def fake_approve(task_id):
        return {"error": "task is running, not awaiting_approval"}

    monkeypatch.setattr(routes, "approve_task", fake_approve)
    response = client.post("/tasks/some-id/approve")
    assert response.status_code == 400


def test_get_task_pr_not_found(client, monkeypatch):
    import src.api.routes.tasks as routes

    async def fake_get(task_id):
        return None

    monkeypatch.setattr(routes, "get_task", fake_get)
    response = client.get("/tasks/missing/pr")
    assert response.status_code == 404
