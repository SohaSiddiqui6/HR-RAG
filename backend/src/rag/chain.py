"""Question -> answer: condense the query, classify what retrieval found, and
either generate a grounded answer or return a no-answer outcome.

Retrieval + rerank live in :mod:`src.rag.retriever`; the prompt templates in
:mod:`src.rag.prompts`. This module is the orchestration:

    small talk?  -> canned reply
    condense (follow-ups)  -> standalone query
    retrieve + classify:
        chunks cleared the relevance floor  -> generate
        related but below it                -> Outcome.NEEDS_HUMAN
        nothing related                     -> Outcome.OUT_OF_SCOPE
"""

from __future__ import annotations

import functools
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from src import config
from src.guardrails.input import smalltalk_reply, strip_injection
from src.rag.prompts import ANSWER_PROMPT, CONDENSE_PROMPT
from src.rag.retriever import retrieve


class Outcome(str, Enum):
    """What the pipeline decided to do with a question."""

    ANSWERED = "answered"
    NEEDS_HUMAN = "needs_human"  # HR-related but not in the docs -> offer a handoff
    OUT_OF_SCOPE = "out_of_scope"  # nothing related in the docs


# Returned verbatim when retrieval finds nothing related (out of scope).
NO_ANSWER = "I don't have information about that in the available HR policies."
# Returned when the question looks HR-related but the policies don't cover it.
NEEDS_HUMAN_ANSWER = (
    "I couldn't find this in the current HR policies. You can open a request and "
    "the HR team will follow up."
)

# Recent conversation turns, oldest first: (role, content).
History = list[tuple[str, str]]


@dataclass
class Answer:
    text: str
    outcome: Outcome = Outcome.ANSWERED
    sources: List[dict] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)


@functools.lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=config.LLM_MODEL,
        temperature=0,
        max_tokens=config.MAX_ANSWER_TOKENS,
    )


# --- retrieval classification --------------------------------------------


@dataclass
class _Retrieval:
    docs: List[Document]  # cleared the relevance floor; empty means "no answer"
    outcome: Outcome


def _retrieve_relevant(
    query: str, run_config: RunnableConfig | None, where: Any | None
) -> _Retrieval:
    """Retrieve + rerank, then classify: answerable / needs a human / out of scope."""
    ranked = retrieve(query, run_config, where)
    kept = [
        d
        for d in ranked
        if d.metadata.get("relevance_score", 0.0) >= config.RELEVANCE_THRESHOLD
    ]
    if kept:
        return _Retrieval(kept, Outcome.ANSWERED)

    top = max((d.metadata.get("relevance_score", 0.0) for d in ranked), default=0.0)
    outcome = (
        Outcome.NEEDS_HUMAN if top >= config.ESCALATION_FLOOR else Outcome.OUT_OF_SCOPE
    )
    return _Retrieval([], outcome)


def _no_answer_text(outcome: Outcome) -> str:
    return NEEDS_HUMAN_ANSWER if outcome is Outcome.NEEDS_HUMAN else NO_ANSWER


# --- prompt assembly -----------------------------------------------------


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
    """The `{history}` slot in ``ANSWER_PROMPT`` — empty when there is no history."""
    if not history:
        return ""
    return f"Earlier in this conversation (for context only):\n{_transcript(history)}\n\n"


def _format_docs(docs: List[Document]) -> str:
    # Retrieved text is untrusted — neutralise obvious injection strings before it
    # goes into the prompt (the prompt also tells the model to treat it as data).
    return "\n\n".join(
        f"[Source: {d.metadata.get('source')} | Page: {d.metadata.get('page_no')} | "
        f"Heading: {d.metadata.get('headings')}]\n{strip_injection(d.page_content)}"
        for d in docs
    )


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


# --- answering ---------------------------------------------------------


def answer_question(
    question: str,
    history: History | None = None,
    run_config: RunnableConfig | None = None,
    where: Any | None = None,
) -> Answer:
    """Condense, retrieve + classify, and generate a grounded, cited answer.

    If no retrieved chunk clears ``RELEVANCE_THRESHOLD`` the answer carries a
    ``needs_human`` / ``out_of_scope`` outcome instead of a generated response.
    ``where`` is the retrieval authorization filter; ``run_config`` is threaded
    into every model call for tracing.
    """
    small_talk = smalltalk_reply(question)
    if small_talk is not None:
        return Answer(text=small_talk)

    history = history or []
    query = _condense(question, history, run_config)
    result = _retrieve_relevant(query, run_config, where)
    if not result.docs:
        return Answer(text=_no_answer_text(result.outcome), outcome=result.outcome)

    response = get_llm().invoke(
        ANSWER_PROMPT.format_messages(
            history=_history_block(history),
            context=_format_docs(result.docs),
            question=question,
        ),
        config=run_config,
    )
    return Answer(
        text=str(response.content),
        sources=_sources(result.docs),
        contexts=[d.page_content for d in result.docs],
    )


def stream_answer(
    question: str,
    history: History | None = None,
    run_config: RunnableConfig | None = None,
    where: Any | None = None,
) -> Iterator[str | Answer]:
    """Same rules as ``answer_question``, streamed.

    Yields answer text token-by-token, then a final :class:`Answer` carrying the
    full text, sources, and outcome. The no-answer paths yield their fixed text
    as a single chunk.
    """
    small_talk = smalltalk_reply(question)
    if small_talk is not None:
        yield small_talk
        yield Answer(text=small_talk)
        return

    history = history or []
    query = _condense(question, history, run_config)
    result = _retrieve_relevant(query, run_config, where)
    if not result.docs:
        text = _no_answer_text(result.outcome)
        yield text
        yield Answer(text=text, outcome=result.outcome)
        return

    messages = ANSWER_PROMPT.format_messages(
        history=_history_block(history),
        context=_format_docs(result.docs),
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
        sources=_sources(result.docs),
        contexts=[d.page_content for d in result.docs],
    )
