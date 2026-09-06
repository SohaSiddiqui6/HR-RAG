"""Query functions for the conversation store. One thin layer over SQLModel."""

from __future__ import annotations

from sqlmodel import Session, select

from src.db.models import (
    DEFAULT_TITLE,
    Conversation,
    IngestedDocument,
    Message,
    utcnow,
)


def list_conversations(session: Session) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())  # type: ignore[attr-defined]
    return list(session.exec(stmt))


def create_conversation(session: Session, title: str = DEFAULT_TITLE) -> Conversation:
    conversation = Conversation(title=title)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def get_conversation(session: Session, conversation_id: str) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def add_message(
    session: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    outcome: str = "answered",
    trace_id: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources or [],
        outcome=outcome,
        trace_id=trace_id,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def get_message(session: Session, message_id: str) -> Message | None:
    return session.get(Message, message_id)


def set_escalation(session: Session, message_id: str, data: dict) -> Message | None:
    """Record the handoff outcome (`{channel, reference, url}`) on a message."""
    message = session.get(Message, message_id)
    if message is None:
        return None
    message.escalation = data
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def recent_messages(
    session: Session, conversation_id: str, limit: int
) -> list[Message]:
    """The last ``limit`` messages of a conversation, oldest first."""
    if limit <= 0:
        return []
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())  # type: ignore[attr-defined]
        .limit(limit)
    )
    return list(reversed(session.exec(stmt).all()))


def set_title_if_default(session: Session, conversation_id: str, title: str) -> None:
    conversation = session.get(Conversation, conversation_id)
    if conversation and conversation.title == DEFAULT_TITLE:
        conversation.title = title[:60]
        session.add(conversation)
        session.commit()


def touch(session: Session, conversation_id: str) -> None:
    conversation = session.get(Conversation, conversation_id)
    if conversation:
        conversation.updated_at = utcnow()
        session.add(conversation)
        session.commit()


def delete_conversation(session: Session, conversation_id: str) -> bool:
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        return False
    session.delete(conversation)
    session.commit()
    return True


# --- Ingestion manifest (see src.rag.ingest) ------------------------------


def list_ingested_documents(session: Session) -> list[IngestedDocument]:
    stmt = select(IngestedDocument).order_by(IngestedDocument.source)  # type: ignore[arg-type]
    return list(session.exec(stmt))


def get_ingest_manifest(session: Session) -> dict[str, str]:
    """``{filename: sha256}`` for every PDF already in Chroma."""
    return {d.source: d.sha256 for d in list_ingested_documents(session)}


def upsert_ingested_document(
    session: Session,
    source: str,
    sha256: str,
    chunk_count: int,
    ocr_used: bool = False,
) -> None:
    """Record (or update) one PDF's manifest row after its chunks are upserted."""
    row = session.get(IngestedDocument, source)
    if row is None:
        row = IngestedDocument(source=source, sha256=sha256, chunk_count=chunk_count)
    row.sha256 = sha256
    row.chunk_count = chunk_count
    row.ocr_used = ocr_used
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
