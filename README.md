# DocuAsk

[![CI](https://github.com/Sriyansh-28/docuask/actions/workflows/ci.yml/badge.svg)](https://github.com/Sriyansh-28/docuask/actions/workflows/ci.yml)

A full-stack **document Q&A web app**: upload a PDF (or paste text), ask
questions in a chat box, and get answers with the **source passage** shown —
plus a live feedback/telemetry dashboard.

> **Status:** Session 4 — the feedback/telemetry layer is live. Every question
> is logged to SQLite with its measured latency, answers carry 👍/👎 buttons,
> and a `/#/dashboard` page shows total questions, median latency, and
> thumbs-up rate live from the DB, plus a questions-over-time bar. Retrieval is
> a lightweight BM25 + FAISS (TF-IDF) hybrid. Final polish/deploy is the last
> session (see [`PROJECT_SPEC.md`](./PROJECT_SPEC.md)).

## Run it (one command)

```bash
docker compose up --build
```

Then open **http://localhost:5173** — you should see **"API status: ok"**
pulled live from the backend at http://localhost:8000/health.

## Run without Docker (dev)

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

In dev the Vite server proxies `/api/*` to the backend, so no CORS setup is
needed. In the Docker setup, nginx reverse-proxies `/api/` to the API service.

## Tests

```bash
cd backend
pytest
```

## Project structure

```
docuask/
  backend/            # FastAPI app, tests
    app/main.py       # GET /health + CORS
    tests/            # pytest suite
  frontend/           # Vite + React + Tailwind
    src/App.jsx       # calls /health and renders the status
  docker-compose.yml  # brings both services up
  .github/workflows/  # CI: pytest on every push
```

## Tech stack

- **Frontend:** React + Vite + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Tests:** pytest
- **CI:** GitHub Actions (pytest on every push)
- **Local orchestration:** Docker Compose

## Roadmap

See [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) for the full plan:

1. ✅ Skeleton end to end (health check wired browser → API)
2. Upload & parse flow (PDF/text → chunked, indexed)
3. Retrieval + chat loop (BM25 + FAISS, source passages)
4. Data-collection & feedback layer (SQLite, 👍/👎, `/stats`, dashboard)
5. Polish, tests, live deploy

## License

[MIT](./LICENSE)
