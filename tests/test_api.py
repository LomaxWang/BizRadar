"""Integration tests for the FastAPI app (api.server)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env_override(tmp_path, monkeypatch):
    """Override settings so the app uses temp paths and a known API key."""
    monkeypatch.setenv("IDEAHUNTER_SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("IDEAHUNTER_API_KEY", "test-secret")
    monkeypatch.setenv("LLM_API_KEY", "fake-llm-key")
    # Clear the lru_cache so Settings re-reads env
    from config.settings import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def client():
    from api.server import app
    return TestClient(app, raise_server_exceptions=False)


AUTH_HEADER = {"Authorization": "Bearer test-secret"}


# ---------- /health ----------


class TestHealth:
    def test_health_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_no_auth_required(self, client: TestClient):
        """Health endpoint should work without auth."""
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------- Auth enforcement ----------


class TestAuth:
    def test_ideas_without_auth_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/ideas")
        assert resp.status_code == 401

    def test_ideas_wrong_token_returns_401(self, client: TestClient):
        resp = client.get(
            "/api/v1/ideas",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_scan_without_auth_returns_401(self, client: TestClient):
        resp = client.post(
            "/api/v1/tasks/scan",
            json={"source": "v2ex"},
        )
        assert resp.status_code == 401


# ---------- POST /api/v1/tasks/scan ----------


class TestScan:
    def test_invalid_source_returns_400(self, client: TestClient):
        resp = client.post(
            "/api/v1/tasks/scan",
            json={"source": "nonexistent_source"},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 400

    def test_valid_source_returns_task_id(self, client: TestClient):
        """v2ex is a known source; the endpoint should create a task (background)."""
        resp = client.post(
            "/api/v1/tasks/scan",
            json={"source": "v2ex"},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["task_id"].startswith("tsk_")
        assert body["data"]["status"] == "pending"


# ---------- GET /api/v1/ideas ----------


class TestListIdeas:
    def test_empty_ideas(self, client: TestClient):
        resp = client.get("/api/v1/ideas", headers=AUTH_HEADER)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["total"] == 0
        assert body["data"]["items"] == []

    def test_ideas_with_query_params(self, client: TestClient):
        resp = client.get(
            "/api/v1/ideas",
            params={"min_score": 50, "page": 1, "size": 10},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200


# ---------- GET /api/v1/tasks/{task_id} ----------


class TestGetTask:
    def test_nonexistent_task_404(self, client: TestClient):
        resp = client.get(
            "/api/v1/tasks/tsk_nonexistent",
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 404
