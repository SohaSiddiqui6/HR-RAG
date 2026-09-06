"""Retrieval + generation: server-side hybrid search, Cohere rerank, grounded answer.

``ChromaHybridRetriever`` is a thin ``BaseRetriever`` over Chroma's server-side
RRF fusion of the dense and sparse indexes. It is wrapped in a Cohere reranker
(``retrieve`` retries that call on trial-key 429s), and ``answer_question`` feeds
the reranked chunks to the LLM with a citation prompt.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, List, Optional

from chromadb import K, Knn, Rrf, Search
from cohere.errors import TooManyRequestsError
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import ConfigDict

from src import config
from src.rag.vectorstore import get_collection

RRF_K = 60
MISSING_RANK = 1000  # rank for docs absent from one of the two rankings

# Returned verbatim when retrieval finds nothing relevant (see RELEVANCE_THRESHOLD).
NO_ANSWER = "I don't have information about that in the available HR policies."

# Recent conversation turns, oldest first: (role, content).
History = list[tuple[str, str]]

PROMPT = ChatPromptTemplate.from_template(
    """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Cite each fact inline in square brackets using the source name, e.g. [remote-work-policy].
Do not invent citations.

{history}Context:
{context}

Question: {question}

Helpful Answer:"""
)

CONDENSE_PROMPT = ChatPromptTemplate.from_template(
    """Given the conversation so far and a follow-up question, rewrite the follow-up
as a standalone question that can be understood without the conversation.
If it is already standalone, or starts a new topic, return it unchanged.
Return only the question.

Conversation:
{history}

Follow-up: {question}
Standalone question:"""
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


@functools.lru_cache(maxsize=1)
def get_retriever() -> ContextualCompressionRetriever:
    """Hybrid retriever wrapped in a Cohere reranker (built once, then cached)."""
    hybrid = ChromaHybridRetriever(collection=get_collection())
    compressor = CohereRerank(model=config.RERANK_MODEL, top_n=config.RERANK_TOP_N)
    return ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=hybrid
    )


@functools.lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model=config.LLM_MODEL, temperature=0)


def retrieve(question: str, run_config: RunnableConfig | None = None) -> List[Document]:
    """Hybrid retrieve + Cohere rerank, retrying on the rerank rate limit (429)."""
    retriever = get_retriever()
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


def _relevant_docs(
    question: str, run_config: RunnableConfig | None
) -> List[Document]:
    """Retrieve + rerank, keeping only chunks above the relevance floor."""
    return [
        d
        for d in retrieve(question, run_config)
        if d.metadata.get("relevance_score", 0.0) >= config.RELEVANCE_THRESHOLD
    ]


def _sources(docs: List[Document]) -> List[dict]:
    return [
        {
            "source": d.metadata.get("source"),
            "page_no": d.metadata.get("page_no"),
            "headings": d.metadata.get("headings"),
        }
        for d in docs
    ]


def _transcript(history: History) -> str:
    labels = {"user": "User", "assistant": "Assistant"}
    return "\n".join(f"{labels.get(role, role)}: {text}" for role, text in history)


def _history_block(history: History) -> str:
    """The `{history}` slot in ``PROMPT`` — empty when there is no history."""
    if not history:
        return ""
    return f"Earlier in this conversation (for context only):\n{_transcript(history)}\n\n"


def _condense(
    question: str, history: History, run_config: RunnableConfig | None
) -> str:
    """Rewrite a follow-up into a standalone query for retrieval. No-op without history."""
    if not history:
        return question
    response = get_llm().invoke(
        CONDENSE_PROMPT.format_messages(
            history=_transcript(history), question=question
        ),
        config=run_config,
    )
    return str(response.content).strip() or question


def answer_question(
    question: str,
    history: History | None = None,
    run_config: RunnableConfig | None = None,
) -> Answer:
    """Retrieve, rerank, and generate a grounded, cited answer.

    On a follow-up (``history`` non-empty) the question is first condensed into a
    standalone query for retrieval; generation still sees the original question
    plus the recent turns. If no retrieved chunk clears ``RELEVANCE_THRESHOLD``
    the question is out of scope and ``NO_ANSWER`` is returned without generating.
    ``run_config`` is a LangChain config threaded into every model call for tracing.
    """
    history = history or []
    docs = _relevant_docs(_condense(question, history, run_config), run_config)
    if not docs:
        return Answer(text=NO_ANSWER)

    response = get_llm().invoke(
        PROMPT.format_messages(
            history=_history_block(history),
            context=_format_docs(docs),
            question=question,
        ),
        config=run_config,
    )
    return Answer(
        text=str(response.content),
        sources=_sources(docs),
        contexts=[d.page_content for d in docs],
    )


def stream_answer(
    question: str,
    history: History | None = None,
    run_config: RunnableConfig | None = None,
) -> Iterator[str | Answer]:
    """Same retrieval + abstention + condensing rules as ``answer_question``, streamed.

    Yields answer text token-by-token, then a final :class:`Answer` carrying the
    full text plus sources and contexts. The out-of-scope path yields
    ``NO_ANSWER`` as a single chunk.
    """
    history = history or []
    docs = _relevant_docs(_condense(question, history, run_config), run_config)
    if not docs:
        yield NO_ANSWER
        yield Answer(text=NO_ANSWER)
        return

    messages = PROMPT.format_messages(
        history=_history_block(history),
        context=_format_docs(docs),
        question=question,
    )
    parts: List[str] = []
    for chunk in get_llm().stream(messages, config=run_config):
        text = str(chunk.content)
        if text:
            parts.append(text)
            yield text

    yield Answer(
        text="".join(parts),
        sources=_sources(docs),
        contexts=[d.page_content for d in docs],
    )
