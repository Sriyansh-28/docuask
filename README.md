---
title: DocuAsk
emoji: 📄
colorFrom: green
colorTo: gray
sdk: static
app_build_command: cd frontend && npm ci && npm run build
app_file: frontend/dist/index.html
pinned: false
license: mit
---

# DocuAsk

[![CI](https://github.com/Sriyansh-28/docuask/actions/workflows/ci.yml/badge.svg)](https://github.com/Sriyansh-28/docuask/actions/workflows/ci.yml)

**DocuAsk** is a full-stack document Q&A web app. Upload a PDF (or paste text),
ask questions in a chat box, and get answers with the **source passage** shown
underneath — then rate each answer 👍/👎 and watch the usage metrics update on a
live dashboard. It's a small, end-to-end product loop: a React front end, a
FastAPI back end, a lightweight retrieval layer, and a SQLite telemetry layer,
all runnable with one command and deployable as a single container.

🔗 **Live demo:** [huggingface.co/spaces/Sri-28/docuask](https://huggingface.co/spaces/Sri-28/docuask)
_(goes live once the Space is created — see [Deploy](#deploy-hugging-face-spaces))_

## Screenshots

| Chat — answer with source passage | Dashboard — live metrics |
| :---: | :---: |
| ![Chat view](docs/screenshots/chat.png) | ![Dashboard view](docs/screenshots/dashboard.png) |

## Features

- **Upload & parse** — drag-and-drop a PDF or paste text; the backend extracts
  (pypdf), chunks, and indexes it in memory. Encrypted / broken / non-PDF /
  empty / oversize inputs all fail with a clear, friendly message.
- **Chat with sources** — every answer shows the passage it was drawn from, so
  the retrieval is transparent.
- **Hybrid retrieval** — BM25 (`rank_bm25`) combined with a FAISS cosine search
  over TF-IDF vectors; deliberately lightweight, no heavyweight model.
- **Feedback & telemetry** — each question is logged to SQLite with its measured
  latency; 👍/👎 feedback and a `/dashboard` page show total questions, median
  latency, and thumbs-up rate live from the DB.

## Run it (one command)

```bash
docker compose up --build
```

Then open **http://localhost:5173**. The frontend calls the API through nginx,
so there's nothing else to configure.

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
needed.

## Tests

```bash
cd backend
pytest
```

The suite covers `/health`, upload success and every failure path, retrieval and
`/ask`, `/feedback`, `/stats`, and the combined deploy entrypoint. CI runs it on
every push.

## API

| Method | Path                | Purpose                                            |
| ------ | ------------------- | -------------------------------------------------- |
| GET    | `/health`           | Liveness probe.                                    |
| POST   | `/documents`        | Ingest a PDF file or raw text → `document_id`.     |
| GET    | `/documents/{id}`   | Document metadata.                                 |
| POST   | `/ask`              | `{document_id, question}` → answer + source passage. |
| POST   | `/feedback`         | Attach 👍/👎 (`up`/`down`) to an interaction.       |
| GET    | `/stats`            | Totals, median latency, thumbs-up rate, over-time. |

## Deploy

The frontend deploys to a **Hugging Face Static Space** and the API to any host
that runs a Python web process. They're wired together with one Space variable —
no rebuild needed to change the API URL.

### 1. Frontend → Hugging Face Static Space

The README front matter (`sdk: static`) tells HF to run the
`app_build_command` (`cd frontend && npm ci && npm run build`) and serve
`frontend/dist`.

1. Create a new **Space** → **Static** SDK, owner `Sri-28`, name `docuask`.
2. Push this repo to the Space (the [`sync-to-hf`](./.github/workflows/sync-to-hf.yml)
   workflow does this automatically — see below).
3. In the Space's **Settings → Variables**, add `DOCUASK_API_URL` set to your
   deployed API's URL. The frontend reads it at runtime via
   `window.huggingface.variables`, so you can change it without rebuilding.

The Space serves at **https://sri-28-docuask.static.hf.space**.

### 2. Backend → Railway

The API is a standard uvicorn app. On **Railway**:

1. **New Project → Deploy from GitHub repo** → select `docuask`.
2. Open the service → **Settings → Root Directory** = `backend`. This makes
   [`backend/railway.json`](./backend/railway.json) build
   [`backend/Dockerfile`](./backend/Dockerfile) (which installs faiss's
   `libgomp1` and honors Railway's injected `$PORT`).
3. **Settings → Networking → Generate Domain** to get a public URL.
4. *(Optional)* Add a **Volume** mounted at `/data` and a variable
   `DOCUASK_DB=/data/docuask.db` so telemetry persists across restarts.
5. Copy the public URL — you'll set it as `DOCUASK_API_URL` in the HF Space
   (step 3 above).

The Static Space origin (`https://sri-28-docuask.static.hf.space`) is already in
the backend's default CORS allow-list; add more via the `CORS_ORIGINS` env var.
See [`backend/.env.example`](./backend/.env.example).

> Other hosts work too: any Docker host can build `backend/Dockerfile`, and
> native-Python hosts (Render, …) can use [`backend/Procfile`](./backend/Procfile).

### Keep the demo in sync automatically

The [`sync-to-hf`](./.github/workflows/sync-to-hf.yml) workflow mirrors `main` to
your Space on every push. Configure it once under **Settings → Secrets and
variables → Actions**:

- Secret `HF_TOKEN` — a Hugging Face token with write scope. **This is the only
  required step** (username defaults to `Sri-28`, Space to `docuask`).
- Optionally override the `HF_USERNAME` / `HF_SPACE` variables.

Until `HF_TOKEN` is set the workflow no-ops, so it never fails the branch.

> **One-origin alternative:** the root [`Dockerfile`](./Dockerfile) +
> [`app/server.py`](./backend/app/server.py) build a single image that serves the
> frontend and API together under one origin (API mounted at `/api`, no CORS).
> Use this on any Docker host if you'd rather run one service than two.

## Project structure

```
docuask/
  backend/              # FastAPI app + tests
    app/
      main.py           # API: /health, /documents, /ask, /feedback, /stats
      parsing.py        # PDF/text extraction + chunking
      retrieval.py      # BM25 + FAISS (TF-IDF) hybrid index
      store.py          # in-memory document store
      db.py             # SQLite interaction telemetry
      server.py         # combined static + API entrypoint (deploy)
    tests/              # pytest suite
  frontend/             # Vite + React + Tailwind
    src/
      App.jsx           # layout + hash routing (Chat / Dashboard)
      DocumentUploader.jsx, Chat.jsx, Dashboard.jsx
  Dockerfile            # single-image build for Hugging Face Spaces
  docker-compose.yml    # local: frontend + backend together
  .github/workflows/    # CI: pytest + frontend build on every push
```

## Tech stack

- **Frontend:** React + Vite + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Retrieval:** BM25 + FAISS over TF-IDF
- **Persistence:** SQLite (interaction telemetry)
- **Tests:** pytest
- **CI:** GitHub Actions (pytest + build on every push)
- **Deploy:** Hugging Face Static Space (frontend) + any Python host (API); Docker Compose locally

## Roadmap

See [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) for the full plan:

1. ✅ Skeleton end to end (health check wired browser → API)
2. ✅ Upload & parse flow (PDF/text → chunked, indexed)
3. ✅ Retrieval + chat loop (BM25 + FAISS, source passages)
4. ✅ Data-collection & feedback layer (SQLite, 👍/👎, `/stats`, dashboard)
5. ✅ Polish, tests, deploy (single-image Docker Space)

## License

[MIT](./LICENSE)
