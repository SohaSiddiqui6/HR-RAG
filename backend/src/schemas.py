"""Request / response models for the HTTP API — the contract the frontend consumes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str


class SourceOut(BaseModel):
    source: str
    page_no: int | None = None
    headings: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceOut] = []
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime


class ConversationRead(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class CreateConversationRequest(BaseModel):
    question: str | None = None


class SendMessageRequest(BaseModel):
    question: str = ""


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


class WorkspaceStats(BaseModel):
    documents: list[str] = []
    document_count: int
    chunk_count: int
