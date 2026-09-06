"""Retrieval: server-side hybrid search fused with RRF, then a Cohere rerank.

``ChromaHybridRetriever`` is a thin ``BaseRetriever`` over Chroma's server-side
RRF fusion of the dense (OpenAI) and sparse (BM25) indexes. ``retrieve()`` wraps
it in a Cohere reranker and retries the rerank on trial-key rate limits. The
``where`` argument is the authorization boundary — a Chroma metadata filter that
limits which chunks the query can even see.
"""

from __future__ import annotations

import functools
import time
from typing import Any, List, Optional

from chromadb import K, Knn, Rrf, Search
from cohere.errors import TooManyRequestsError
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableConfig
from pydantic import ConfigDict

from src import config
from src.rag.vectorstore import get_collection

RRF_K = 60
MISSING_RANK = 1000  # rank for docs absent from one of the two rankings


class ChromaHybridRetriever(BaseRetriever):
    """Dense + BM25 lexical retrieval, fused server-side with RRF."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    collection: Any
    sparse_key: str = config.SPARSE_KEY
    k: int = config.RETRIEVAL_K
    dense_weight: float = config.DENSE_WEIGHT
    sparse_weight: float = config.SPARSE_WEIGHT
    candidate_pool: int = config.CANDIDATE_POOL
    where: Optional[Any] = None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        hybrid_rank = Rrf(
            ranks=[
                Knn(
                    query=query,
                    return_rank=True,
                    limit=self.candidate_pool,
                    default=MISSING_RANK,
                ),
                Knn(
                    query=query,
                    key=self.sparse_key,
                    return_rank=True,
                    limit=self.candidate_pool,
                    default=MISSING_RANK,
                ),
            ],
            weights=[self.dense_weight, self.sparse_weight],
            k=RRF_K,
        )

        search = (
            Search()
            .rank(hybrid_rank)
            .limit(self.k)
            .select(K.DOCUMENT, K.SCORE, K.METADATA)
        )
        if self.where is not None:
            search = search.where(self.where)

        rows = self.collection.search(search).rows()[0]
        return [
            Document(
                page_content=row["document"],
                metadata={**(row.get("metadata") or {}), "rrf_score": row.get("score")},
            )
            for row in rows
        ]


@functools.lru_cache(maxsize=1)
def _get_reranker() -> CohereRerank:
    return CohereRerank(model=config.RERANK_MODEL, top_n=config.RERANK_TOP_N)


def _build_retriever(where: Any | None = None) -> ContextualCompressionRetriever:
    """Hybrid retriever + Cohere reranker, optionally scoped by a metadata filter."""
    hybrid = ChromaHybridRetriever(collection=get_collection(), where=where)
    return ContextualCompressionRetriever(
        base_compressor=_get_reranker(), base_retriever=hybrid
    )


def retrieve(
    question: str,
    run_config: RunnableConfig | None = None,
    where: Any | None = None,
) -> List[Document]:
    """Hybrid retrieve + Cohere rerank, retrying on the rerank rate limit (429)."""
    retriever = _build_retriever(where)
    for attempt in range(1, config.RERANK_MAX_RETRIES + 1):
        try:
            return retriever.invoke(question, config=run_config)
        except TooManyRequestsError:
            if attempt >= config.RERANK_MAX_RETRIES:
                raise
            delay = config.RERANK_RETRY_BASE_DELAY * attempt
            print(
                f"Cohere rerank rate-limited; retrying in {delay:.0f}s "
                f"(attempt {attempt + 1}/{config.RERANK_MAX_RETRIES})"
            )
            time.sleep(delay)
    raise RuntimeError("unreachable: RERANK_MAX_RETRIES must be >= 1")
