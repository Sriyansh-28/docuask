"""DocuAsk FastAPI application.

Session 1 scope: a minimal, end-to-end skeleton (``GET /health`` + CORS).
Session 2 adds the upload & parse flow (``POST /documents``) — a PDF or raw
text is extracted, chunked, and stored in memory keyed by a document id.
Retrieval and telemetry endpoints are added in later sessions.
"""

import logging
import os
import time
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__, db, generate
from .generate import generate_answer, llm_available
from .parsing import DocumentError, chunk_text, extract_pdf_text
from .retrieval import DocumentIndex, best_sentence
from .store import store

logger = logging.getLogger("docuask")

# Reject anything larger than this before parsing, so a huge upload can't
# exhaust memory. 10 MB comfortably covers real documents.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Comma-separated list of allowed origins. Defaults cover the Vite dev server,
# a locally served production build, and the DocuAsk Hugging Face Static Space
# (the deployed frontend). Override in deployment via the CORS_ORIGINS env var.
_DEFAULT_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,"
    "https://sri-28-docuask.static.hf.space"
)
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
def health() -> dict[str, object]:
    """Liveness probe. Also reports the running version and whether LLM answer
    generation is configured, which makes deploys easy to verify."""
    return {"status": "ok", "version": __version__, **generate.status()}


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


class AskRequest(BaseModel):
    document_id: str
    question: str


@app.post("/ask")
def ask(req: AskRequest) -> dict[str, object]:
    """Answer a question about a stored document.

    Runs hybrid retrieval over the document's chunks and returns the extractive
    answer plus the source passage it came from, so the UI can show its work.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    doc = store.get(req.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Build the index on first use and cache it on the document. Index
    # construction is one-off setup, so it is excluded from the measured
    # answer latency.
    if doc.index is None:
        doc.index = DocumentIndex(doc.chunks)

    start = time.perf_counter()
    hits = doc.index.search(question, k=3)
    top_index, score = hits[0]
    passage = doc.chunks[top_index]

    # Prefer an LLM answer grounded in the top passages; fall back to the
    # extractive best-sentence when no API key is configured or the call fails.
    top_passages = [doc.chunks[i] for i, _ in hits]
    answer = generate_answer(question, top_passages)
    generated = answer is not None
    if not generated:
        answer = best_sentence(passage, question)
    latency_ms = int((time.perf_counter() - start) * 1000)

    interaction_id = db.log_interaction(doc.id, question, answer, latency_ms)

    return {
        "interaction_id": interaction_id,
        "document_id": doc.id,
        "question": question,
        "answer": answer,
        "generated": generated,
        "source_passage": passage,
        "chunk_index": top_index,
        "score": round(score, 4),
        "latency_ms": latency_ms,
    }


class FeedbackRequest(BaseModel):
    interaction_id: str
    feedback: Literal["up", "down"]


@app.post("/feedback")
def feedback(req: FeedbackRequest) -> dict[str, object]:
    """Attach a 👍/👎 rating to a previously logged interaction."""
    if not db.set_feedback(req.interaction_id, req.feedback):
        raise HTTPException(status_code=404, detail="Interaction not found.")
    return {
        "status": "ok",
        "interaction_id": req.interaction_id,
        "feedback": req.feedback,
    }


@app.get("/stats")
def stats() -> dict[str, object]:
    """Aggregate telemetry for the dashboard: totals, latency, thumbs-up rate."""
    return db.get_stats()
