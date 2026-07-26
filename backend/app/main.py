"""DocuAsk FastAPI application.

Session 1 scope: a minimal, end-to-end skeleton (``GET /health`` + CORS).
Session 2 adds the upload & parse flow (``POST /documents``) — a PDF or raw
text is extracted, chunked, and stored in memory keyed by a document id.
Retrieval and telemetry endpoints are added in later sessions.
"""

import logging
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .parsing import DocumentError, chunk_text, extract_pdf_text
from .store import store

logger = logging.getLogger("docuask")

# Reject anything larger than this before parsing, so a huge upload can't
# exhaust memory. 10 MB comfortably covers real documents.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Comma-separated list of allowed origins. Defaults cover the Vite dev server
# and a locally served production build. Override in deployment via env var.
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app = FastAPI(
    title="DocuAsk API",
    version=__version__,
    description="Backend for the DocuAsk document Q&A web app.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the frontend and Docker healthcheck."""
    return {"status": "ok"}


def _looks_like_pdf(file: UploadFile) -> bool:
    name = (file.filename or "").lower()
    return name.endswith(".pdf") or (file.content_type == "application/pdf")


@app.post("/documents", status_code=201)
async def create_document(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> dict[str, object]:
    """Ingest a PDF upload or raw text.

    Exactly one of ``file`` or ``text`` should be supplied. The text is
    extracted, chunked, and stored; the response carries the id the client uses
    to ask questions later. All foreseeable failures return a 4xx with a
    human-readable ``detail`` the UI can show directly.
    """
    filename: str | None = None

    if file is not None and file.filename:
        if not _looks_like_pdf(file):
            raise HTTPException(status_code=415, detail="Only PDF files are supported.")

        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
            )
        if not data:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        try:
            extracted = extract_pdf_text(data)
        except DocumentError as exc:
            logger.warning("PDF parse failed for %r: %s", file.filename, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        filename = file.filename

    elif text is not None and text.strip():
        if len(text.encode("utf-8")) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Text is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
            )
        extracted = text

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide a PDF file or some text to ingest.",
        )

    chunks = chunk_text(extracted)
    if not chunks:
        raise HTTPException(status_code=400, detail="No usable text was found.")

    doc = store.add(chunks=chunks, num_chars=len(extracted), filename=filename)
    logger.info("Ingested document %s (%d chunks, %d chars)", doc.id, doc.num_chunks, doc.num_chars)

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "num_chunks": doc.num_chunks,
        "num_chars": doc.num_chars,
        "status": "ready",
    }


@app.get("/documents/{document_id}")
def get_document(document_id: str) -> dict[str, object]:
    """Return metadata for a stored document, or 404 if it is unknown."""
    doc = store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "num_chunks": doc.num_chunks,
        "num_chars": doc.num_chars,
        "status": "ready",
    }
