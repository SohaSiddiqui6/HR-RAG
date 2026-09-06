"""Central configuration, loaded from environment variables (see .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"

# --- Ingestion corpus source --------------------------------------------
# "local" reads PDFs from DOCS_DIR; "supabase" pulls them from a private
# Supabase Storage bucket via the service-role key. The per-file SHA-256
# manifest lives in Postgres (``ingested_document`` table) either way.
DOCS_SOURCE = os.getenv("DOCS_SOURCE", "local")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")  # server-only
DOCS_BUCKET = os.getenv("DOCS_BUCKET", "hr-policy-docs")
DOCS_PREFIX = os.getenv("DOCS_PREFIX", "")  # optional subfolder within the bucket

# --- API keys ---------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "")
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
# Tracing is enabled whenever this is set (secret key + host read by the SDK).
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")

# --- Conversation store ----------------------------------------------------
# Postgres (Supabase) connection string. Tests override this with sqlite://.
DATABASE_URL = os.getenv("DATABASE_URL", "")
# Recent messages replayed as context for follow-up questions (0 disables it).
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "4"))

# --- Escalation (human handoff) -------------------------------------------
# "none" (default, logs only) or "slack".
ESCALATION_BACKEND = os.getenv("ESCALATION_BACKEND", "none")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# --- Chroma Cloud ----------------------------------------------------------
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "production-rag")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "research_papers_hybrid")
# Metadata key the sparse (BM25) vectors live under; must match between the
# schema definition and the Knn(key=...) used at query time.
SPARSE_KEY = os.getenv("SPARSE_KEY", "sparse_embedding")

# --- Models --------------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank-v3.5")
# Generation-time answer cap (the output guardrail keeps a hard char limit too).
MAX_ANSWER_TOKENS = int(os.getenv("MAX_ANSWER_TOKENS", "800"))

# --- Chunking ----------------------------------------------------------
CHUNK_TOKENIZER = os.getenv("CHUNK_TOKENIZER", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "512"))

# --- Retrieval -------------------------------------------------------
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "20"))
CANDIDATE_POOL = int(os.getenv("CANDIDATE_POOL", "200"))
DENSE_WEIGHT = float(os.getenv("DENSE_WEIGHT", "0.6"))
SPARSE_WEIGHT = float(os.getenv("SPARSE_WEIGHT", "0.4"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))
# Drop reranked chunks below this Cohere relevance score. If nothing clears it,
# the question is not answered from the docs (no LLM call) rather than trusting
# the model to abstain.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.3"))
# When nothing clears RELEVANCE_THRESHOLD but the top chunk still scores at least
# this, the question looks HR-related-but-uncovered -> offer a human handoff.
# Below it, the question is treated as out of scope.
ESCALATION_FLOOR = float(os.getenv("ESCALATION_FLOOR", "0.08"))
# Cohere trial keys allow only 10 requests/minute; retry the rerank on a 429
# with linear backoff (base_delay, 2*base_delay, ...) instead of failing.
RERANK_MAX_RETRIES = int(os.getenv("RERANK_MAX_RETRIES", "5"))
RERANK_RETRY_BASE_DELAY = float(os.getenv("RERANK_RETRY_BASE_DELAY", "7.0"))
