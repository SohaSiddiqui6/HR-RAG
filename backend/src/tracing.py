"""Langfuse tracing + online scoring.

`trace_config(trace_id)` gives the RAG chain a LangChain callback config that
streams spans (retriever -> rerank -> LLM, with tokens and cost) to Langfuse.
`score()` attaches a cheap deterministic quality signal to that same trace —
online monitoring, no extra LLM call. `new_trace_id()` ties a request's spans and
scores together and is also handed to the client so user feedback can reference
it. Everything is a no-op when `LANGFUSE_PUBLIC_KEY` is unset.

LLM-as-a-judge scoring in production runs as a sampled, asynchronous Langfuse
Evaluator (configured in the Langfuse UI), never on the request path — see
evaluation/README.md.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langfuse.types import TraceContext

from src import config

_ENABLED = bool(config.LANGFUSE_PUBLIC_KEY)

ScoreType = Literal["NUMERIC", "CATEGORICAL", "BOOLEAN"]


def new_trace_id() -> str | None:
    """A fresh trace id for one request, or None when tracing is off."""
    return get_client().create_trace_id() if _ENABLED else None


def trace_config(trace_id: str | None = None) -> RunnableConfig | None:
    if not _ENABLED:
        return None
    context = TraceContext(trace_id=trace_id) if trace_id else None
    return {"callbacks": [CallbackHandler(trace_context=context)]}


def score(
    trace_id: str | None, name: str, value: float | str, data_type: ScoreType
) -> None:
    if _ENABLED and trace_id:
        get_client().create_score(
            trace_id=trace_id, name=name, value=value, data_type=data_type
        )
