"""DocuAsk FastAPI application.

Session 1 scope: a minimal, end-to-end skeleton. Exposes GET /health and
configures CORS so the Vite dev frontend can call the API in development.
Upload, retrieval, and telemetry endpoints are added in later sessions.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__

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
