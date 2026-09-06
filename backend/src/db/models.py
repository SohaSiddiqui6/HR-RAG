"""SQLModel tables for the conversation store."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

DEFAULT_TITLE = "New conversation"


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    title: str = DEFAULT_TITLE
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    messages: list["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "Message.created_at",
        },
    )


class Message(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    conversation_id: str = Field(foreign_key="conversation.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    sources: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    # "answered" | "needs_human" | "out_of_scope" (see rag.chain.Outcome)
    outcome: str = "answered"
    # {channel, reference, url} once a human handoff has been raised for this message
    escalation: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    created_at: datetime = Field(default_factory=utcnow)

    conversation: Optional[Conversation] = Relationship(back_populates="messages")
