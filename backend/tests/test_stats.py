"""Tests for the data-collection & feedback layer (Session 4)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TEXT = (
    "The mitochondria is the powerhouse of the cell. "
    "The Eiffel Tower is located in Paris, France."
)


def _ask() -> dict:
    doc_id = client.post("/documents", data={"text": TEXT}).json()["document_id"]
    response = client.post(
        "/ask", json={"document_id": doc_id, "question": "Where is the Eiffel Tower?"}
    )
    assert response.status_code == 200
    return response.json()


def test_ask_persists_interaction_with_latency():
    result = _ask()
    assert "interaction_id" in result
    assert isinstance(result["latency_ms"], int)
    assert result["latency_ms"] >= 0

    stats = client.get("/stats").json()
    assert stats["total_questions"] == 1
    assert stats["median_latency_ms"] is not None


def test_feedback_updates_stats():
    result = _ask()
    response = client.post(
        "/feedback",
        json={"interaction_id": result["interaction_id"], "feedback": "up"},
    )
    assert response.status_code == 200

    stats = client.get("/stats").json()
    assert stats["thumbs_up"] == 1
    assert stats["thumbs_down"] == 0
    assert stats["thumbs_up_rate"] == 1.0


def test_thumbs_up_rate_reflects_mix():
    up = _ask()
    down = _ask()
    client.post("/feedback", json={"interaction_id": up["interaction_id"], "feedback": "up"})
    client.post("/feedback", json={"interaction_id": down["interaction_id"], "feedback": "down"})

    stats = client.get("/stats").json()
    assert stats["total_questions"] == 2
    assert stats["thumbs_up_rate"] == 0.5


def test_invalid_feedback_value_is_rejected():
    result = _ask()
    response = client.post(
        "/feedback",
        json={"interaction_id": result["interaction_id"], "feedback": "meh"},
    )
    assert response.status_code == 422


def test_feedback_unknown_interaction_returns_404():
    response = client.post(
        "/feedback", json={"interaction_id": "does-not-exist", "feedback": "up"}
    )
    assert response.status_code == 404


def test_stats_empty_by_default():
    stats = client.get("/stats").json()
    assert stats["total_questions"] == 0
    assert stats["median_latency_ms"] is None
    assert stats["thumbs_up_rate"] is None
    assert stats["questions_over_time"] == []
