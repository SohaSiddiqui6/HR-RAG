"""Query functions for the conversation store. One thin layer over SQLModel."""

from __future__ import annotations

from sqlmodel import Session, select

from src.db.models import DEFAULT_TITLE, Conversation, Message, utcnow


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
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources or [],
    )
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
