"""Retrieval + generation: server-side hybrid search, Cohere rerank, grounded answer.

``ChromaHybridRetriever`` is a thin ``BaseRetriever`` over Chroma's server-side
RRF fusion of the dense and sparse indexes. It is wrapped in a Cohere reranker,
and ``answer_question`` feeds the reranked chunks to the LLM with a citation
prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from chromadb import K, Knn, Rrf, Search
from langchain_cohere import CohereRerank
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from pydantic import ConfigDict

try:  # location moved across langchain 0.3 releases
    from langchain.retrievers.contextual_compression import (
        ContextualCompressionRetriever,
    )
except ImportError:  # pragma: no cover
    from langchain_classic.retrievers.contextual_compression import (
        ContextualCompressionRetriever,
    )

from src import config
from src.vectorstore import get_collection

RRF_K = 60
MISSING_RANK = 1000  # rank for docs absent from one of the two rankings

PROMPT = ChatPromptTemplate.from_template(
    """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Always cite the source, page_no, and headings from the context in your answer.

Context:
{context}

Question: {question}

Helpful Answer:"""
)


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


@dataclass
class Answer:
    text: str
    sources: List[dict] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)


def _format_docs(docs: List[Document]) -> str:
    return "\n\n".join(
        f"Source: {d.metadata.get('source')}, Page: {d.metadata.get('page_no')}, "
        f"Heading: {d.metadata.get('headings')}\nContent: {d.page_content}"
        for d in docs
    )


_retriever: Optional[Any] = None
_llm: Optional[ChatOpenAI] = None


def get_retriever():
    """Hybrid retriever wrapped in a Cohere reranker (built once, then cached)."""
    global _retriever
    if _retriever is None:
        hybrid = ChromaHybridRetriever(collection=get_collection())
        compressor = CohereRerank(
            model=config.RERANK_MODEL, top_n=config.RERANK_TOP_N
        )
        _retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=hybrid
        )
    return _retriever


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=config.LLM_MODEL, temperature=0)
    return _llm


def answer_question(question: str) -> Answer:
    """Retrieve, rerank, and generate a grounded, cited answer."""
    docs = get_retriever().invoke(question)
    context = _format_docs(docs)
    response = get_llm().invoke(
        PROMPT.format_messages(context=context, question=question)
    )
    sources = [
        {
            "source": d.metadata.get("source"),
            "page_no": d.metadata.get("page_no"),
            "headings": d.metadata.get("headings"),
        }
        for d in docs
    ]
    return Answer(
        text=response.content,
        sources=sources,
        contexts=[d.page_content for d in docs],
    )
