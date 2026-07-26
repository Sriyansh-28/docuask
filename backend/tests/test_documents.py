"""Tests for the upload & parse flow (Session 2).

Covers the happy path (raw text) and, per the acceptance criteria, the
parse-failure paths: non-PDF files, broken PDFs, password-protected PDFs,
empty input, and oversize input.
"""

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import MAX_UPLOAD_BYTES, app

client = TestClient(app)


def _encrypted_pdf_bytes(password: str = "secret") -> bytes:
    """Build a small, password-protected PDF in memory."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # RC4 avoids a hard dependency on the `cryptography` package in CI.
    writer.encrypt(user_password=password, algorithm="RC4-128")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_create_document_from_text():
    body = "DocuAsk turns a document into a searchable index. " * 40
    response = client.post("/documents", data={"text": body})
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["num_chunks"] >= 1
    assert payload["num_chars"] == len(body)
    assert payload["filename"] is None

    # The returned id resolves to a stored document.
    fetched = client.get(f"/documents/{payload['document_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["document_id"] == payload["document_id"]


def test_empty_text_is_rejected():
    response = client.post("/documents", data={"text": "   "})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_missing_input_is_rejected():
    response = client.post("/documents")
    assert response.status_code == 400


def test_non_pdf_file_is_rejected():
    response = client.post(
        "/documents",
        files={"file": ("notes.png", b"\x89PNG\r\n", "image/png")},
    )
    assert response.status_code == 415
    assert "PDF" in response.json()["detail"]


def test_broken_pdf_is_rejected():
    # A .pdf name but garbage bytes — pypdf cannot read it.
    response = client.post(
        "/documents",
        files={"file": ("broken.pdf", b"this is definitely not a pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_encrypted_pdf_is_rejected():
    response = client.post(
        "/documents",
        files={"file": ("secret.pdf", _encrypted_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 400
    assert "password" in response.json()["detail"].lower()


def test_oversize_text_is_rejected():
    huge = "a" * (MAX_UPLOAD_BYTES + 1)
    response = client.post("/documents", data={"text": huge})
    assert response.status_code == 413


def test_unknown_document_returns_404():
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404
