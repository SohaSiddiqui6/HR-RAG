"""FastAPI entrypoint: the JSON API for the HR assistant frontend."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from src import config, guardrails
from src.db import store
from src.db.session import get_engine, get_session, init_db
from src.escalation import EscalationRequest, get_escalation
from src.rag.chain import Answer, stream_answer
from src.rag.vectorstore import get_workspace_stats
from src.schemas import (
    ConversationRead,
    ConversationSummary,
    CreateEscalationRequest,
    ErrorResponse,
    EscalationOut,
    HealthResponse,
    SendMessageRequest,
    WorkspaceStats,
)
from src.tracing import trace_config


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="HR-RAG", lifespan=lifespan)


def _not_found() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "Conversation not found"})


def _sse(event_type: str, **data) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def _answer_stream(conversation_id: str, question: str) -> Iterator[str]:
    """SSE event stream: `token`* then `done`, or an `error` event on failure.

    Runs after the response has started, so it opens its own DB session (the
    request-scoped one from `Depends` is already closed). Reads recent history
    for follow-up context, persists the user message up front, and persists the
    assistant message once generation completes.
    """
    where = guardrails.where_filter(guardrails.retrieval_context())

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
                question, history=history, where=where, run_config=trace_config()
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
            store.add_message(
                session,
                conversation_id,
                "assistant",
                guarded.answer,
                sources=answer.sources,
                outcome=answer.outcome.value,
            )
            store.set_title_if_default(session, conversation_id, question)
            store.touch(session, conversation_id)
            yield _sse("done")
        except Exception as exc:  # noqa: BLE001 - reported to the client as an SSE error
            yield _sse("error", error=str(exc))


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/workspace", response_model=WorkspaceStats)
def workspace() -> dict:
    """Coverage summary for the right-hand pane: indexed documents and chunk count."""
    return get_workspace_stats()


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations(session: Session = Depends(get_session)):
    return store.list_conversations(session)


@app.post("/api/conversations", response_model=ConversationRead)
def create_conversation(session: Session = Depends(get_session)):
    return store.create_conversation(session)


@app.get(
    "/api/conversations/{conversation_id}",
    response_model=ConversationRead,
    responses={404: {"model": ErrorResponse}},
)
def get_conversation(conversation_id: str, session: Session = Depends(get_session)):
    conversation = store.get_conversation(session, conversation_id)
    if conversation is None:
        return _not_found()
    return conversation


@app.post(
    "/api/conversations/{conversation_id}/messages/stream",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def stream_message(
    conversation_id: str,
    payload: SendMessageRequest,
    session: Session = Depends(get_session),
):
    """Ask a question; the grounded answer streams back as Server-Sent Events."""
    if store.get_conversation(session, conversation_id) is None:
        return _not_found()

    ok, reason = guardrails.check_input(payload.question)
    if not ok:
        return JSONResponse(status_code=400, content={"error": reason})

    return StreamingResponse(
        _answer_stream(conversation_id, payload.question),
        media_type="text/event-stream",
    )


@app.post(
    "/api/conversations/{conversation_id}/escalation",
    response_model=EscalationOut,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def escalate(
    conversation_id: str,
    payload: CreateEscalationRequest,
    session: Session = Depends(get_session),
):
    """Hand an unanswered question to a human (Slack). Idempotent per message."""
    message = store.get_message(session, payload.message_id)
    if message is None or message.conversation_id != conversation_id:
        return _not_found()
    if message.outcome != "needs_human":
        return JSONResponse(
            status_code=409, content={"error": "This message can't be escalated."}
        )
    if message.escalation is not None:
        return message.escalation

    result = get_escalation().submit(
        EscalationRequest(
            subject=payload.subject or "HR question",
            body=payload.body,
            conversation_id=conversation_id,
        )
    )
    data = {"channel": result.channel, "reference": result.reference, "url": result.url}
    store.set_escalation(session, payload.message_id, data)
    return data


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, session: Session = Depends(get_session)):
    store.delete_conversation(session, conversation_id)
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
