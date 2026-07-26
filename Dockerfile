# Single-image build for Hugging Face Spaces (Docker SDK).
# Stage 1 builds the React frontend; stage 2 runs the FastAPI backend and
# serves the built frontend from the same origin on port 7860.

# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # outputs /fe/dist

# ---- Stage 2: backend + static assets ----
FROM python:3.11-slim
WORKDIR /app

# libgomp1 is required at runtime by faiss-cpu (OpenMP).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /fe/dist ./static

# HF Spaces expose port 7860. /tmp is writable regardless of the runtime user;
# mount HF persistent storage and set DOCUASK_DB=/data/docuask.db to keep
# telemetry across restarts.
ENV DOCUASK_DB=/tmp/docuask.db
EXPOSE 7860

CMD ["uvicorn", "app.server:root", "--host", "0.0.0.0", "--port", "7860"]
