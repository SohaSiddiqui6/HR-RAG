"""FastAPI entrypoint: the JSON API for the HR assistant frontend."""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Response
from fastapi.responses import JSONResponse
from sqlmodel import Session

from src import guardrails
from src.db import store
from src.db.models import Message
from src.db.session import get_session, init_db
from src.rag.chain import answer_question
from src.rag.vectorstore import get_workspace_stats
from src.schemas import (
    ConversationRead,
    ConversationSummary,
    CreateConversationRequest,
    ErrorResponse,
    HealthResponse,
    SendMessageRequest,
    SendMessageResponse,
    WorkspaceStats,
)
from src.tracing import trace_config


class GuardrailError(Exception):
    """A question the guardrails rejected — surfaced as HTTP 400 `{error}`."""


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="HR-RAG", lifespan=lifespan)


@app.exception_handler(GuardrailError)
def _guardrail_handler(_, exc: GuardrailError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


def _answer(session: Session, conversation_id: str, question: str) -> tuple[Message, Message]:
    """Guardrail-check, answer, and persist the user + assistant messages."""
    ok, reason = guardrails.check_question(question)
    if not ok:
        raise GuardrailError(reason)

    result = answer_question(question, run_config=trace_config())

    user_message = store.add_message(session, conversation_id, "user", question)
    assistant_message = store.add_message(
        session,
        conversation_id,
        "assistant",
        guardrails.check_answer(result.text),
        sources=result.sources,
    )
    store.set_title_if_default(session, conversation_id, question)
    store.touch(session, conversation_id)
    return user_message, assistant_message


def _not_found() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "Conversation not found"})


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


@app.post(
    "/api/conversations",
    response_model=ConversationRead,
    responses={400: {"model": ErrorResponse}},
)
def create_conversation(
    payload: CreateConversationRequest,
    session: Session = Depends(get_session),
):
    conversation = store.create_conversation(session)
    if payload.question:
        _answer(session, conversation.id, payload.question)
        session.refresh(conversation)
    return conversation


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
    "/api/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    session: Session = Depends(get_session),
):
    if store.get_conversation(session, conversation_id) is None:
        return _not_found()
    user_message, assistant_message = _answer(session, conversation_id, payload.question)
    return {"user_message": user_message, "assistant_message": assistant_message}


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, session: Session = Depends(get_session)):
    store.delete_conversation(session, conversation_id)
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
