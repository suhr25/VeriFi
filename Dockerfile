# VeriFi production image: builds the React frontend, then serves it and the
# FastAPI backend from one process. Used by render.yaml and docker compose.

# ---- 1. Frontend build -------------------------------------------------------
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Empty = same-origin API calls (this server serves the frontend). Only set
# it when building a frontend that talks to an API on another origin.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- 2. Python runtime -------------------------------------------------------
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface

# CPU-only torch first: the default Linux wheel pulls several GB of CUDA
# libraries this app never uses (embeddings run on CPU).
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY --from=frontend-build /frontend/dist /app/frontend/dist
RUN mkdir -p /app/data && useradd --create-home --uid 10001 verifi && chown -R verifi /app
USER verifi

EXPOSE 8000
# Render (and most hosts) assign the port through $PORT. The IPO seed is
# idempotent (updates in place), so it runs on every start to keep the
# database's IPO data in step with scripts/seed_ipo.py; a failure is logged
# but never stops the server from starting.
CMD ["sh", "-c", "python -m scripts.seed_ipo || echo 'IPO seed failed - continuing'; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
