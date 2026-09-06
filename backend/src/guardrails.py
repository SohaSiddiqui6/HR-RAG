"""Lightweight input/output checks around the RAG chain."""

from __future__ import annotations

MAX_QUESTION_LENGTH = 500

_BLOCKED_TERMS = (
    "ignore previous instructions",
    "system prompt",
)


def check_question(question: str) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for an incoming question."""
    text = (question or "").strip()
    if not text:
        return False, "Question is empty."
    if len(text) > MAX_QUESTION_LENGTH:
        return False, "Question is too long."
    lowered = text.lower()
    if any(term in lowered for term in _BLOCKED_TERMS):
        return False, "Question rejected by guardrails."
    return True, ""


def check_answer(answer: str) -> str:
    """Post-process a generated answer before returning it to the user."""
    return (answer or "").strip()
