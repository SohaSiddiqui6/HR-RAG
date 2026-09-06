# Backend

FastAPI service: a retrieval-augmented Q&A API over HR / company policy documents,
plus conversation history. For the full picture and diagrams see
[../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

**RAG pipeline** — **Docling** parses the policy PDFs and **HybridChunker** splits
them → chunks are upserted to a **Chroma Cloud** collection with a dense (OpenAI)
and a sparse (BM25) index side by side → queries run **server-side hybrid search
fused with RRF**, get reranked by **Cohere**, and the top chunks go to
**GPT-4o-mini** for a grounded, cited answer. If no reranked chunk clears the
relevance threshold, the max rerank score decides the outcome: an HR-related but
uncovered question (`>= ESCALATION_FLOOR`) is marked `needs_human` and the UI
offers a handoff to a person; anything lower is `out_of_scope` and declined. No
LLM call on either path.

**Conversations** are persisted in Postgres (Supabase) via SQLModel. On a
follow-up, the last few turns are condensed into a standalone query before
retrieval, so pronouns and "what about…" questions resolve (`HISTORY_TURNS`).

**Guardrails** (`src/guardrails/`) wrap the pipeline without touching it:
`check_input` runs before retrieval (empty / length / off-topic / prompt
injection → HTTP 400; greetings get a canned reply with no retrieval);
`check_output` runs on the finished answer before it is
stored (empty → fallback, fabricated citations stripped, obviously ungrounded
answers replaced, secrets redacted, length capped) and returns a validated
`{answer, citations, answerable}`. Retrieved chunks are treated as untrusted data
(prompt boundary + injection scrub). `authorization.py` is where tenant/role
retrieval filtering plugs in once auth exists.

**Escalation** (`src/escalation/`) — a `needs_human` answer can be handed to a
person via `POST /api/conversations/{id}/escalation` (one per message, idempotent).
`get_escalation()` selects the backend from `ESCALATION_BACKEND`: `NullEscalation`
(default, logs only) or `SlackEscalation` (incoming webhook). A new backend
(Jira, email) is one file implementing `submit()`. The decision to escalate is
deterministic (the score threshold above) — the model isn't in that loop.

## Structure

```
backend/
├── src/
│   ├── config.py            # settings from .env
│   ├── app.py               # FastAPI app + every route
│   ├── streaming.py         # the SSE answer pipeline (persist -> stream -> guard -> score)
│   ├── schemas.py           # request / response models (the API contract)
│   ├── tracing.py           # Langfuse callback + online scores (no-op without keys)
│   ├── guardrails/
│   │   ├── input.py         # empty / length / off-topic / prompt-injection / small-talk
│   │   ├── output.py        # empty / length / citation / grounding / secret redaction
│   │   └── authorization.py # retrieval tenant/role filter boundary (stub — no auth yet)
│   ├── escalation/
│   │   ├── __init__.py     # Escalation protocol + get_escalation()
│   │   ├── null.py         # default — logs only
│   │   └── slack.py        # incoming-webhook notification
│   ├── rag/
│   │   ├── chain.py         # condense -> classify -> generate / abstain / escalate
│   │   ├── retriever.py     # hybrid search (dense + BM25 + RRF) + Cohere rerank
│   │   ├── prompts.py       # LLM prompt templates
│   │   ├── vectorstore.py   # Chroma Cloud client + dense/sparse schema
│   │   └── ingest.py        # Docling -> chunk -> upsert  (python -m src.rag.ingest)
│   └── db/
│       ├── models.py        # SQLModel tables
│       ├── session.py       # engine + get_session()
│       └── store.py         # query functions
├── scripts/sanity_check.py  # dense vs sparse retrieval leg check
├── evaluation/              # Langfuse experiment over a 30-item golden set
│   └── (see evaluation/README.md)
├── tests/                   # mirrors src/: api · rag · guardrails · escalation · evaluation
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
