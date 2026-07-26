"""Combined ASGI app for single-container deploys (Hugging Face Spaces).

Serves the built frontend as static files and mounts the API under ``/api`` so
the browser only ever talks to one origin (no CORS, one demo URL). The
frontend's default API base is ``/api``, so no build-time config is needed.

Local dev and docker-compose keep using ``app.main`` directly; this module is
only the entrypoint for the single-image deployment.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .main import app as api_app

_STATIC_DIR = os.getenv(
    "STATIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
)

root = FastAPI(title="DocuAsk")
root.mount("/api", api_app)

# Mounted last so the API prefix wins; guarded so importing this module without
# a built frontend (e.g. in tests) doesn't fail.
if os.path.isdir(_STATIC_DIR):
    root.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
