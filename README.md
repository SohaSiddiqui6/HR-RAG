# HR-RAG

An HR assistant that answers questions about company policy PDFs with **grounded,
cited** answers. It distinguishes three things it can do with a question —
**answer** it from the documents, **decline** it as out of scope, or **escalate**
it to a human — and decides which deterministically (a reranker-score threshold),
never by trusting the model to know when it doesn't know.

```
├── backend/    FastAPI · hybrid retrieval (Chroma dense + BM25 + RRF) · Cohere rerank
│               · GPT-4o-mini · Postgres · guardrails · Langfuse · Slack handoff
└── frontend/   React + TypeScript SPA (Vite · Tailwind · TanStack Query · SSE streaming)
```

## Run — local dev

```bash
# terminal 1 — API on :8000
cd backend && uv sync && cp .env.example .env   # fill in the keys
uv run uvicorn src.app:app --reload

# terminal 2 — UI on :5173 (proxies /api → :8000)
cd frontend && npm install && npm run dev
```

## Run — one container

The whole app (React SPA served by FastAPI from one origin):

```bash
docker compose up --build          # → http://localhost:8000
# or: docker build -t hr-rag . && docker run -p 8000:8000 --env-file backend/.env hr-rag
```

The image is **serving-only** (~1 GB) — the ingestion stack (Docling/transformers/torch,
~2 GB) is an optional dependency group the request path never imports, so it's
left out and `POST /api/ingest` returns 501. Ingestion runs as a separate job:
`cd backend && uv sync --group ingestion && uv run python -m src.rag.ingest`.
See [docs/ARCHITECTURE.md §7](docs/ARCHITECTURE.md).

## Deploy

One EC2 instance, `docker run`, no VPC/ALB/proxy — step by step in
**[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Docs

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the full picture: system
  context, the answer flow, retrieval, guardrails, the answer/abstain/escalate
  decision, ingestion, evaluation & observability, and the design tradeoffs.
- [backend/README.md](backend/README.md) · [frontend/README.md](frontend/README.md) — setup and layout.
- [backend/evaluation/README.md](backend/evaluation/README.md) — the RAG evaluation.
- [docs/DEPLOY.md](docs/DEPLOY.md) — deploy to a single AWS EC2 box.
