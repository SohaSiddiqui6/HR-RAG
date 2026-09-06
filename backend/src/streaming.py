"""The streaming answer pipeline behind `POST /conversations/{id}/messages/stream`.

`answer_stream` runs *after* the HTTP response has started, so it opens its own DB
session (the request-scoped one is already closed). It:

    1. loads recent history and persists the user message
    2. streams answer tokens as SSE `token` events
    3. runs the output guardrails on the finished answer
    4. records deterministic monitoring scores (Tier 1 — no LLM call)
    5. persists the guarded assistant message and emits `done`

Any failure becomes an SSE `error` event rather than a broken stream.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from sqlmodel import Session

from src import config, guardrails, tracing
from src.db import store
from src.db.session import get_engine
from src.guardrails.output import GuardedAnswer, grounding_ratio
from src.rag.chain import Answer, Outcome, stream_answer


def _sse(event_type: str, **data) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def _score(trace_id: str | None, answer: Answer, guarded: GuardedAnswer) -> None:
    """Deterministic online-monitoring scores — no LLM call (Tier 1)."""
    tracing.score(trace_id, "outcome", answer.outcome.value, "CATEGORICAL")
    if answer.outcome is Outcome.ANSWERED:
        tracing.score(
            trace_id,
            "grounded",
            grounding_ratio(guarded.answer, answer.contexts),
            "NUMERIC",
        )
        tracing.score(trace_id, "cited", float(bool(guarded.citations)), "BOOLEAN")


def answer_stream(conversation_id: str, question: str) -> Iterator[str]:
    """SSE event stream: `token`* then `done`, or an `error` event on failure."""
    where = guardrails.where_filter(guardrails.retrieval_context())
    trace_id = tracing.new_trace_id()

    with Session(get_engine()) as session:
        history = [
            (m.role, m.content)
            for m in store.recent_messages(
                session, conversation_id, config.HISTORY_TURNS
            )
        ]
        store.add_message(session, conversation_id, "user", question)
        try:
            answer: Answer | None = None
            for item in stream_answer(
                question,
                history=history,
                where=where,
                run_config=tracing.trace_config(trace_id),
            ):
                if isinstance(item, Answer):
                    answer = item
                else:
                    yield _sse("token", text=item)
            assert answer is not None  # stream_answer always ends with an Answer

            guarded = guardrails.check_output(
                answer.text,
                sources=answer.sources,
                contexts=answer.contexts,
                abstained=not answer.sources,
            )
            _score(trace_id, answer, guarded)
            store.add_message(
                session,
                conversation_id,
                "assistant",
                guarded.answer,
                sources=answer.sources,
                outcome=answer.outcome.value,
                trace_id=trace_id,
            )
            store.set_title_if_default(session, conversation_id, question)
            store.touch(session, conversation_id)
            yield _sse("done")
        except Exception as exc:  # noqa: BLE001 - reported to the client as an SSE error
            yield _sse("error", error=str(exc))
