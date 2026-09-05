# HR-RAG

A retrieval-augmented Q&A app over HR / company policy documents.

Pipeline: **Docling** parses the policy PDFs and **HybridChunker** splits them ->
chunks are upserted to a **Chroma Cloud** collection that maintains a dense
(OpenAI embeddings) and a sparse (BM25) index side by side -> queries run
**server-side hybrid search fused with RRF**, get reranked by **Cohere**, and the
top chunks are passed to **GPT-4o-mini** for a grounded, cited answer. The API is
served with **FastAPI** / **uvicorn**.

## Structure

```
HR-RAG/
├── src/
│   ├── app.py          # FastAPI: GET / , GET /health , POST /api/ask
│   ├── config.py       # settings + API keys from .env
│   ├── vectorstore.py  # Chroma Cloud client + dense/sparse collection schema
│   ├── ingest.py       # Docling -> chunk -> upsert  (python -m src.ingest)
│   ├── rag_chain.py    # hybrid retriever + Cohere rerank + answer generation
│   └── guardrails.py   # input / output checks
├── scripts/
│   └── sanity_check.py # dense vs sparse retrieval leg check
├── evaluation/
│   ├── eval_questions.json   # 25-question golden set
│   └── run_evaluation.py     # citation accuracy + LLM-judge groundedness + latency
├── tests/
├── static/ · templates/     # minimal chat UI
├── docs/                     # policy PDFs + ingestion manifest
├── pyproject.toml · requirements.txt · .env.example · Procfile
```

## Setup

Uses [uv](https://docs.astral.sh/uv/). `pyproject.toml` is the source of truth;
`requirements.txt` is kept for platforms that need it (`uv export --no-dev -o requirements.txt`).

```bash
uv sync                       # create .venv and install everything (incl. dev)
cp .env.example .env          # then fill in the 4 API keys
```

Required keys (see [.env.example](.env.example)): `OPENAI_API_KEY`,
`CHROMA_API_KEY`, `CHROMA_TENANT`, `COHERE_API_KEY`.

<details><summary>without uv</summary>

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
</details>

## Usage

```bash
uv run python -m src.ingest                # build / update the vector store
uv run python -m scripts.sanity_check "PTO carryover limit"   # verify hybrid search
uv run python -m src.app                    # dev server -> http://localhost:8000
uv run uvicorn src.app:app --reload         # ... or run uvicorn directly
uv run python -m evaluation.run_evaluation  # score the golden set
uv run pytest                               # unit tests
```

The Colab notebook the pipeline was prototyped in is kept at
`Ingestion_Pipeline_New.ipynb` for reference.
