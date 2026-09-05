"""Central configuration, loaded from environment variables (see .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
MANIFEST_PATH = DOCS_DIR / "ingestion_manifest.json"

# --- API keys ---------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "")
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

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

# --- Chunking ----------------------------------------------------------
CHUNK_TOKENIZER = os.getenv("CHUNK_TOKENIZER", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "512"))

# --- Retrieval -------------------------------------------------------
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "20"))
CANDIDATE_POOL = int(os.getenv("CANDIDATE_POOL", "200"))
DENSE_WEIGHT = float(os.getenv("DENSE_WEIGHT", "0.6"))
SPARSE_WEIGHT = float(os.getenv("SPARSE_WEIGHT", "0.4"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))
