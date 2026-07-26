"""Tests for the optional LLM answer layer.

These run without an API key, so they exercise the extractive fallback — the
same path CI takes. The live LLM path is covered by manual verification.
"""

import os

from fastapi.testclient import TestClient

from app import generate
from app.main import app

client = TestClient(app)


def test_llm_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert generate.llm_available() is False
    assert generate.generate_answer("anything", ["a passage"]) is None


def test_ask_falls_back_to_extractive_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text = "The Eiffel Tower is located in Paris, France."
    doc_id = client.post("/documents", data={"text": text}).json()["document_id"]

    response = client.post(
        "/ask", json={"document_id": doc_id, "question": "Where is the Eiffel Tower?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generated"] is False
    assert "Paris" in body["answer"]
