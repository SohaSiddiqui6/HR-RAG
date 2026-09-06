# Backend

FastAPI service: a retrieval-augmented Q&A API over HR / company policy documents,
plus conversation history.

**RAG pipeline** — **Docling** parses the policy PDFs and **HybridChunker** splits
them → chunks are upserted to a **Chroma Cloud** collection with a dense (OpenAI)
and a sparse (BM25) index side by side → queries run **server-side hybrid search
fused with RRF**, get reranked by **Cohere**, and the top chunks go to
**GPT-4o-mini** for a grounded, cited answer. If no reranked chunk clears a
relevance threshold the question is out of scope and answered "not in the
policies" without an LLM call.

**Conversations** are persisted in Postgres (Supabase) via SQLModel. On a
follow-up, the last few turns are condensed into a standalone query before
retrieval, so pronouns and "what about…" questions resolve (`HISTORY_TURNS`).

## Structure

```
backend/
├── src/
│   ├── config.py            # settings from .env
│   ├── app.py               # FastAPI app + routes
│   ├── schemas.py           # request / response models (the API contract)
│   ├── guardrails.py        # input / output checks
│   ├── tracing.py           # Langfuse callback (no-op without keys)
│   ├── rag/
│   │   ├── chain.py         # condense + hybrid retrieve + Cohere rerank + generate
│   │   ├── vectorstore.py   # Chroma Cloud client + dense/sparse schema
│   │   └── ingest.py        # Docling -> chunk -> upsert  (python -m src.rag.ingest)
│   └── db/
│       ├── models.py        # SQLModel tables
│       ├── session.py       # engine + get_session()
│       └── store.py         # query functions
├── scripts/sanity_check.py  # dense vs sparse retrieval leg check
├── evaluation/              # Langfuse experiment over a 30-item golden set
│   └── (see evaluation/README.md)
├── tests/
└── pyproject.toml · uv.lock · requirements.txt · Procfile · .env.example
```

## Setup

Uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env          # then fill in the keys
```

Required (see [.env.example](.env.example)): `OPENAI_API_KEY`, `CHROMA_API_KEY`,
`CHROMA_TENANT`, `COHERE_API_KEY`, `DATABASE_URL` (Supabase Postgres).
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` turn on request tracing and are
required to run the evaluation.

## Usage

```bash
uv run python -m src.rag.ingest             # build / update the vector store
uv run python -m scripts.sanity_check "PTO carryover limit"
uv run uvicorn src.app:app --reload         # http://localhost:8000  (/docs for the schema)
uv run python -m evaluation.run_evaluation  # score the dataset (see evaluation/README.md)
uv run pytest
```
