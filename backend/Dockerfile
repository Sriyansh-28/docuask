FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so they cache across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# curl is used by the docker-compose healthcheck; libgomp1 is required at
# runtime by faiss-cpu (OpenMP) and is not present in the slim base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
