# HR-RAG

An HR assistant that answers questions about company policy documents, with
conversation history — grounded, cited answers with an out-of-scope refusal path.

```
├── backend/    FastAPI · RAG (Docling → Chroma hybrid search → Cohere rerank → GPT-4o-mini) · Postgres
└── frontend/   React + TypeScript SPA (Vite · Tailwind · shadcn · TanStack Query)
```

## Run both

```bash
# terminal 1 — API on :8000
cd backend && uv sync && cp .env.example .env   # fill in the keys
uv run uvicorn src.app:app --reload

# terminal 2 — UI on :5173 (proxies /api → :8000)
cd frontend && npm install && npm run dev
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md)
for details, and [backend/evaluation/README.md](backend/evaluation/README.md) for
the RAG evaluation.
