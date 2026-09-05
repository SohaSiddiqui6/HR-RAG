"""Chroma Cloud connection and the hybrid (dense + sparse) collection schema.

Two indexes are declared on the schema and both are populated by Chroma on
write, straight from the document text:

- Dense  - OpenAI embeddings, cosine space.
- Sparse - BM25 via ``ChromaBm25EmbeddingFunction``, stored under ``SPARSE_KEY``.

The sparse index is a schema-level property fixed at collection-creation time,
so a dense-only collection cannot be upgraded in place - bump ``COLLECTION_NAME``
instead.
"""

from __future__ import annotations

import functools

import chromadb
from chromadb import K, Schema, SparseVectorIndexConfig, VectorIndexConfig
from chromadb.utils.embedding_functions import (
    ChromaBm25EmbeddingFunction,
    OpenAIEmbeddingFunction,
)

from src import config


def _client() -> chromadb.CloudClient:
    return chromadb.CloudClient(
        api_key=config.CHROMA_API_KEY,
        tenant=config.CHROMA_TENANT,
        database=config.CHROMA_DATABASE,
    )


def _schema() -> Schema:
    dense_ef = OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name=config.EMBEDDING_MODEL,
    )
    # Runs locally, no API key. b/k are the standard BM25 knobs; avg_doc_length
    # should roughly match the chunk size in tokens.
    sparse_ef = ChromaBm25EmbeddingFunction(
        k=1.2,
        b=0.75,
        avg_doc_length=256.0,
        token_max_length=40,
    )
    return (
        Schema()
        .create_index(
            config=VectorIndexConfig(space="cosine", embedding_function=dense_ef)
        )
        .create_index(
            config=SparseVectorIndexConfig(
                source_key=K.DOCUMENT, embedding_function=sparse_ef
            ),
            key=config.SPARSE_KEY,
        )
    )


@functools.lru_cache(maxsize=1)
def get_collection():
    """Return the hybrid collection, creating it with the schema if needed."""
    return _client().get_or_create_collection(
        name=config.COLLECTION_NAME,
        schema=_schema(),
    )
