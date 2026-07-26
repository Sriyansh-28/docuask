# DocuAsk — Full-Stack Document Q&A Web App

## Purpose (read first)

A customer-facing web app where a user uploads a PDF (or pastes text), asks
questions in a chat box, and gets answers with the source passage shown. The
retrieval backend is intentionally lightweight — the point of this project is
the front-end product loop and user-facing data collection, not the RAG. Spend
effort on the UI, error handling, and the feedback/telemetry layer.

Target reviewer: general software-engineering apprenticeship (React front-end,
REST API, CI/CD, deployed live URL, product metrics).

## Stack (fixed — do not substitute)

- **Frontend:** React + Vite + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Retrieval:** BM25 + FAISS (keep minimal; a single in-memory index is fine)
- **Persistence:** SQLite (question/answer/latency/feedback log)
- **Tests:** pytest (backend)
- **CI:** GitHub Actions running pytest on every push
- **Deploy:** Docker Compose locally; frontend to Vercel/Netlify, backend to
  Render/Railway

## Repository setup (Session 0)

Public GitHub repo named `docuask` under github.com/Sriyansh-28.

- `git init`, add a Python + Node `.gitignore`, MIT license, `README.md`.
- Structure:

```
docuask/
  backend/        # FastAPI app, retrieval, db, tests
  frontend/       # Vite React app
  docker-compose.yml
  .github/workflows/ci.yml
  README.md
  PROJECT_SPEC.md
```

- First commit: skeleton only. Push to the new remote before writing features.

## Session 1 — Skeleton end to end

Goal: browser shows data fetched from the API.

- FastAPI app with `GET /health` returning `{"status":"ok"}`.
- Vite React app with one page that calls `/health` and renders the status.
- Docker Compose brings both up with one `docker compose up`.
- CORS configured so frontend can call backend in dev.

**Acceptance criteria**

- [x] `docker compose up` starts both services with no errors.
- [x] Opening the frontend URL shows "API status: ok" pulled live from the backend.
- [x] Repo pushed; README has a one-line run instruction.

## Session 2 — Upload & parse flow

Goal: user uploads a PDF; backend extracts and chunks the text.

- `POST /documents` accepts a PDF or raw text, extracts text (pypdf), splits
  into chunks, builds/stores the index in memory keyed by a document id.
- Frontend: drag-and-drop upload widget with loading and success states.
- Handle failures visibly: encrypted PDF, non-PDF file, empty/huge file → clear
  error message in the UI, no crash.

**Acceptance criteria**

- [x] Uploading a normal PDF returns a document id and shows "ready" in the UI.
- [x] Uploading a broken/encrypted PDF shows a friendly error, backend logs it.
- [x] A pytest test covers the parse-failure path.

## Session 3 — Retrieval + chat loop

Goal: the core question→answer experience.

- `POST /ask` takes `{document_id, question}`, runs BM25 + FAISS retrieval,
  returns the answer text plus the top source passage.
- Frontend: chat interface — question input, message history, each answer shows
  the source passage underneath.
- Show a loading indicator while `/ask` is in flight.

**Acceptance criteria**

- [x] Asking a question about an uploaded doc returns a relevant passage.
- [x] The source passage is visibly shown under each answer.
- [x] Empty question or unknown document id is handled gracefully.

## Session 4 — Data-collection & feedback layer (the score-lifting part)

Goal: turn this into a web-enabled system for data collection with product
metrics.

- SQLite table
  `interactions(id, document_id, question, answer, latency_ms, feedback, created_at)`.
- Every `/ask` call logs the row with measured `latency_ms`.
- 👍 / 👎 buttons on each answer → `POST /feedback` updates the row.
- `GET /stats` returns: total questions, median latency, thumbs-up rate.
- A small `/dashboard` page in the frontend reads `/stats` and shows 3 numbers +
  a simple bar of questions-over-time.

**Acceptance criteria**

- [x] Each question persists with its real latency.
- [x] Feedback buttons update the record and reflect in `/stats`.
- [x] Dashboard page renders the three metrics live from the DB.

## Session 5 — Polish, test, deploy

Goal: live URL + green CI + a README a recruiter can skim.

- Backend pytest suite covers `/health`, upload success + failure, `/ask`,
  `/feedback`.
- `.github/workflows/ci.yml` runs pytest on every push; badge in README.
- Deploy backend (Render/Railway) and frontend (Vercel/Netlify); wire the live
  API URL.
- README: one-paragraph description, screenshot/GIF of the chat + dashboard,
  live demo link, run instructions, tech stack.

> Deployed as the single-image combined app (`Dockerfile` + `app/server.py`) on
> **Railway** — one container serving the React frontend and the FastAPI API
> under `/api` from one origin. (A Hugging Face Static Space + separate API is
> also supported; see the README.)

**Acceptance criteria**

- [x] CI badge is green on the default branch.
- [x] Live demo URL works end to end (upload → ask → feedback → dashboard) —
      verified against https://docuask-production-c732.up.railway.app.
- [x] README has a screenshot and the live link.

## Guardrails

- Keep retrieval simple; do not over-engineer the RAG. If a session is running
  long, cut retrieval sophistication, never the front-end or telemetry.
- Only report metrics you actually measured. No invented user counts.
