"""Tests for the combined deploy entrypoint (Session 5).

Ensures the API is reachable under the /api prefix the frontend expects when
both are served from one origin (Hugging Face Space).
"""

from fastapi.testclient import TestClient

from app.server import root

client = TestClient(root)


def test_api_is_mounted_under_api_prefix():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
