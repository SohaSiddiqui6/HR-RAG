"""FastAPI entrypoint: the JSON API for the HR assistant frontend.

Every route lives here; the streaming answer pipeline is in `src.streaming`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from src import guardrails, streaming, tracing
from src.db import store
from src.db.session import get_session, init_db
from src.escalation import EscalationRequest, get_escalation
from src.rag.vectorstore import get_workspace_stats
from src.schemas import (
    ConversationRead,
    ConversationSummary,
    CreateEscalationRequest,
    ErrorResponse,
    EscalationOut,
    FeedbackRequest,
    HealthResponse,
    IngestResponse,
    SendMessageRequest,
    WorkspaceStats,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="HR-RAG", lifespan=lifespan)


def _not_found() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "Conversation not found"})


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/workspace", response_model=WorkspaceStats)
def workspace() -> dict:
    """Coverage summary for the right-hand pane: indexed documents and chunk count."""
    return get_workspace_stats()


@app.post(
    "/api/ingest",
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}},
)
def ingest():
    """Re-scan ``docs/`` and upsert new or changed policy PDFs into the vector store.

    Runs the full pipeline synchronously (Docling parse -> chunk -> Chroma upsert).
    The manifest means unchanged files are skipped, so a no-op re-run is fast; a
    first run or a changed corpus can take minutes. FastAPI runs this sync handler
    in a worker thread, so other requests keep serving while it works.
    """
    # Imported lazily: the ingestion stack (Docling, transformers, torch) is heavy
    # and only this route needs it — keep it out of API startup.
    from src.rag.ingest import run_ingestion

    try:
        return run_ingestion()
    except FileNotFoundError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


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
        streaming.answer_stream(conversation_id, payload.question),
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


@app.post("/api/feedback", status_code=204)
def submit_feedback(payload: FeedbackRequest):
    """Thumbs up/down on an answer -> a Langfuse score on its trace (Tier 2)."""
    tracing.score(payload.trace_id, "user_feedback", float(payload.helpful), "BOOLEAN")
    return Response(status_code=204)


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, session: Session = Depends(get_session)):
    store.delete_conversation(session, conversation_id)
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
