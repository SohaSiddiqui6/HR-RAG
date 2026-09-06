"""Input guardrails: checks on the incoming question before it reaches retrieval."""

from __future__ import annotations

import re

MIN_QUESTION_LENGTH = 3
MAX_QUESTION_LENGTH = 500

# Obvious instruction-override / prompt-injection attempts. Deterministic and
# narrow on purpose — this is not a classifier.
_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all)\b.{0,20}\b(instruction|prompt|rule|context)",
        r"\b(reveal|show|print|repeat|expose|tell me)\b.{0,30}\b(system\s+)?(prompt|instruction)",
        r"\byou are now\b",
        r"\bnew instructions?\s*:",
        r"\bact as\b.{0,20}\b(if|though)\b",
    )
]

# Clearly-not-HR requests. Kept tiny so real policy questions are never rejected;
# the retrieval relevance floor (abstention) handles everything else.
_OFF_TOPIC_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bwrite (me )?(a |an )?(poem|song|story|essay|joke|haiku|script|code|program|function)\b",
        r"\b(what|how)('s| is| are)\b.{0,15}\bweather\b",
        r"\btell me a joke\b",
        r"\btranslate (this|that|it|the following)\b.{0,20}\b(into|to)\b",
        r"\b(who|which team)\b.{0,20}\b(won|winning)\b.{0,20}\b(game|match|cup|election)\b",
    )
]


def contains_injection(text: str) -> bool:
    """True if the text contains an obvious prompt-injection phrase."""
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def strip_injection(text: str) -> str:
    """Replace injection phrases with ``[removed]`` — used to neutralise retrieved chunks."""
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[removed]", text)
    return text


def is_off_topic(text: str) -> bool:
    return any(pattern.search(text) for pattern in _OFF_TOPIC_PATTERNS)


# --- Small talk ----------------------------------------------------------
# Greetings and pleasantries get a friendly canned reply instead of running
# retrieval (which would abstain and read as rude). Patterns are anchored so a
# real question with a greeting prefix ("hi, how much PTO?") still goes to RAG.

_GREETING_REPLY = (
    "Hi! I'm your HR assistant — ask me about company policies, benefits, pay, or time off."
)
_THANKS_REPLY = "You're welcome! Let me know if there's anything else I can help with."
_CAPABILITY_REPLY = (
    "I'm an assistant for company HR policies. I can answer questions about "
    "benefits, leave, pay, conduct, and other handbook topics, with citations to "
    "the source documents."
)

_SMALLTALK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*(hi+|hey+|hello|yo|hiya|greetings)( there| team| folks)?\b[\s!.,]*$", re.IGNORECASE), _GREETING_REPLY),
    (re.compile(r"^\s*good (morning|afternoon|evening)\b[\s!.,]*$", re.IGNORECASE), _GREETING_REPLY),
    (
        re.compile(
            r"^\s*(hi|hey|hello)?[\s,]*how('?s| is| are|'re| are you| have you been)"
            r"(\s+(you|things|it going|your day))?(\s+(doing|going|today))?\s*[?!.]*$",
            re.IGNORECASE,
        ),
        _GREETING_REPLY,
    ),
    (re.compile(r"^\s*(thanks|thank you|thank u|thx|ty|cheers|much appreciated)\b[\s!.,]*$", re.IGNORECASE), _THANKS_REPLY),
    (re.compile(r"^\s*(bye|goodbye|see you|see ya|later|good night)\b[\s!.,]*$", re.IGNORECASE), _THANKS_REPLY),
    (re.compile(r"^\s*(who are you|what can you do|what do you do|how do you work|help)\s*[?!.]*$", re.IGNORECASE), _CAPABILITY_REPLY),
]


def smalltalk_reply(text: str | None) -> str | None:
    """A canned reply for a greeting / thanks / 'who are you', or ``None``."""
    stripped = (text or "").strip()
    for pattern, reply in _SMALLTALK_PATTERNS:
        if pattern.search(stripped):
            return reply
    return None


def check_input(question: str | None) -> tuple[bool, str]:
    """Return ``(ok, reason)``; ``reason`` is a user-facing message when not ok."""
    text = (question or "").strip()
    if not text:
        return False, "Please enter a question."
    if len(text) < MIN_QUESTION_LENGTH:
        return False, "That question is too short — please add a little more detail."
    if len(text) > MAX_QUESTION_LENGTH:
        return False, f"That question is too long (max {MAX_QUESTION_LENGTH} characters)."
    if contains_injection(text):
        return False, "That request can't be processed."
    if is_off_topic(text):
        return False, "I can only help with questions about company HR policies."
    return True, ""
