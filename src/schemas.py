"""Request / response models for the HTTP API — the contract the frontend consumes."""

from __future__ import annotations

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str = ""


class SourceOut(BaseModel):
    source: str
    page_no: int | None = None
    headings: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
