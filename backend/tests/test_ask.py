"""Tests for the retrieval + chat loop (Session 3)."""

from fastapi.testclient import TestClient

from app.main import app
from app.retrieval import DocumentIndex, best_sentence

client = TestClient(app)

FACTS = [
    "The mitochondria is the powerhouse of the cell.",
    "Python is a popular programming language for data science.",
    "The Eiffel Tower is located in Paris, France.",
]


def _ingest(text: str) -> str:
    response = client.post("/documents", data={"text": text})
    assert response.status_code == 201
    return response.json()["document_id"]


def test_index_ranks_relevant_chunk_first():
    index = DocumentIndex(FACTS)
    hits = index.search("Where is the Eiffel Tower?", k=1)
    assert FACTS[hits[0][0]] == FACTS[2]


def test_best_sentence_picks_overlapping_sentence():
    passage = " ".join(FACTS)
    assert "Eiffel" in best_sentence(passage, "Where is the Eiffel Tower?")


def test_ask_returns_relevant_passage_and_answer():
    doc_id = _ingest(" ".join(FACTS))
    response = client.post(
        "/ask",
        json={"document_id": doc_id, "question": "Where is the Eiffel Tower?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Paris" in body["source_passage"]
    assert "Eiffel" in body["answer"] or "Paris" in body["answer"]
    assert body["chunk_index"] >= 0


def test_ask_empty_question_is_rejected():
    doc_id = _ingest(" ".join(FACTS))
    response = client.post("/ask", json={"document_id": doc_id, "question": "   "})
    assert response.status_code == 400


def test_ask_unknown_document_returns_404():
    response = client.post(
        "/ask", json={"document_id": "does-not-exist", "question": "Hello?"}
    )
    assert response.status_code == 404
