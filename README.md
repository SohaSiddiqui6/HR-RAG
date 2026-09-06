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

## Run both

```bash
# terminal 1 — API on :8000
cd backend && uv sync && cp .env.example .env   # fill in the keys
uv run uvicorn src.app:app --reload

# terminal 2 — UI on :5173 (proxies /api → :8000)
cd frontend && npm install && npm run dev
```

## Docs

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the full picture: system
  context, the answer flow, retrieval, guardrails, the answer/abstain/escalate
  decision, ingestion, evaluation & observability, and the design tradeoffs.
- [backend/README.md](backend/README.md) · [frontend/README.md](frontend/README.md) — setup and layout.
- [backend/evaluation/README.md](backend/evaluation/README.md) — the RAG evaluation.
