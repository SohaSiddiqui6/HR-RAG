# syntax=docker/dockerfile:1
#
# One image, the whole app: the built React SPA is served by FastAPI from the
# same origin, so `docker run -p 8000:8000 --env-file backend/.env <image>` gives
# you the entire product at http://localhost:8000.
#
# The image is serving-only — the ingestion stack (Docling / transformers / torch,
# ~2 GB) is an optional dependency group the request path never imports, so it is
# left out. `POST /api/ingest` returns 501 here; ingestion runs as a separate job
# (`uv sync --group ingestion` + `python -m src.rag.ingest`).

# --- 1. build the frontend --------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build                       # -> /web/dist

# --- 2. resolve backend deps (serving only) --------------------------------
FROM python:3.13-slim AS deps
RUN pip install --no-cache-dir uv
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev          # no `dev`, no `ingestion` group

# --- 3. runtime -----------------------------------------------------------
FROM python:3.13-slim AS runtime
RUN useradd --create-home app
WORKDIR /app
COPY --from=deps /app/.venv /app/.venv
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
