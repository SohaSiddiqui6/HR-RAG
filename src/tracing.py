"""Langfuse tracing.

``trace_config()`` returns a LangChain config that streams a call's spans
(retriever → rerank → LLM, with token counts and cost) to Langfuse, or ``None``
when ``LANGFUSE_PUBLIC_KEY`` is unset — so the app runs untraced without keys.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langfuse.langchain import CallbackHandler

from src import config

_handler = CallbackHandler() if config.LANGFUSE_PUBLIC_KEY else None


def trace_config() -> RunnableConfig | None:
    return {"callbacks": [_handler]} if _handler else None
