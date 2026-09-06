"""Output guardrails: checks on the generated answer before it is returned.

``check_output`` is the entry point. It runs: empty check → citation validation →
grounding check → secret redaction → length cap, and returns a validated
:class:`GuardedAnswer`. (Redaction runs last so its ``[redacted-…]`` markers are
not mistaken for citations.) The grounding check is a cheap lexical proxy that
only blocks obviously unsupported answers — real faithfulness scoring is the
offline evaluation and is not repeated here.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger(__name__)

MAX_ANSWER_CHARS = 4000
GROUNDING_MIN_OVERLAP = 0.15

EMPTY_OUTPUT_FALLBACK = (
    "I wasn't able to generate an answer. Please try rephrasing your question."
)
UNGROUNDED_FALLBACK = (
    "I don't have enough information in the HR policies to answer that confidently."
)

# Obvious secrets to redact from model output. Emails are deliberately absent so
# the company's HR contact address is never touched.
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[redacted-api-key]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[redacted-aws-key]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "[redacted-token]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[redacted-token]"),
    (
        re.compile(
            r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z ]+ )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[redacted-private-key]",
    ),
    (
        re.compile(
            r"\b(password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*\S{6,}",
            re.IGNORECASE,
        ),
        r"\1: [redacted]",
    ),
]

_CITATION_RE = re.compile(r"\[([^\[\]]+)\]")
_WORD_RE = re.compile(r"[a-z0-9]{4,}")
_STOPWORDS = {
    "that", "this", "these", "those", "with", "from", "your", "you", "have", "will",
    "which", "there", "their", "about", "would", "should", "could", "when", "what",
    "policy", "policies", "company", "employee", "employees", "please", "also",
}


class GuardedAnswer(BaseModel):
    """The validated answer returned after the output guardrails run."""

    answer: str
    citations: list[str]
    answerable: bool


def redact_secrets(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _citable_stems(sources: list[dict]) -> set[str]:
    """The filename stem of every retrieved source, lower-cased."""
    return {
        Path(source["source"]).stem.lower()
        for source in sources
        if source.get("source")
    }


def validate_citations(
    text: str, sources: list[dict]
) -> tuple[str, list[str], list[str]]:
    """Check every inline ``[...]`` against the retrieved sources.

    A bracket is a real citation if a retrieved source name appears anywhere
    inside it — so both ``[pto-and-leave-policy]`` and the model's verbose
    ``[pto-and-leave-policy.pdf, Page: 3, Heading: ...]`` count. Brackets with no
    known source in them are fabricated and removed. Returns
    ``(cleaned_text, valid_stems, fabricated)``.
    """
    stems = _citable_stems(sources)
    valid: list[str] = []
    fabricated: list[str] = []

    def _check(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        hit = next((stem for stem in stems if stem and stem in inner.lower()), None)
        if hit:
            valid.append(hit)
            return match.group(0)
        fabricated.append(inner)
        return ""

    cleaned = _CITATION_RE.sub(_check, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).replace(" .", ".").strip()
    return cleaned, valid, fabricated


def grounding_ratio(answer: str, contexts: list[str]) -> float:
    """Fraction of the answer's significant words that occur in the retrieved context.

    Deterministic and cheap — a proxy, not a faithfulness score. Returns 1.0 when
    there is nothing to compare against.
    """
    if not contexts:
        return 1.0
    answer_words = {
        w for w in _WORD_RE.findall(answer.lower()) if w not in _STOPWORDS
    }
    if not answer_words:
        return 1.0
    context_words = set(_WORD_RE.findall(" ".join(contexts).lower()))
    return len(answer_words & context_words) / len(answer_words)


def _cap_length(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    head, sep, _ = clipped.rpartition(".")
    return f"{head}." if sep else clipped


def check_output(
    text: str,
    *,
    sources: list[dict],
    contexts: list[str],
    abstained: bool,
) -> GuardedAnswer:
    """Validate and sanitise a generated answer. See the module docstring for order."""
    text = (text or "").strip()
    if not text:
        return GuardedAnswer(answer=EMPTY_OUTPUT_FALLBACK, citations=[], answerable=False)

    # Abstention already handled upstream — pass it through untouched.
    if abstained:
        return GuardedAnswer(answer=text, citations=[], answerable=False)

    text, valid, fabricated = validate_citations(text, sources)
    if fabricated:
        log.warning("dropped fabricated citations: %s", fabricated)

    if grounding_ratio(text, contexts) < GROUNDING_MIN_OVERLAP:
        log.warning("answer failed the grounding check; returning the safe fallback")
        return GuardedAnswer(answer=UNGROUNDED_FALLBACK, citations=[], answerable=False)

    text = _cap_length(redact_secrets(text), MAX_ANSWER_CHARS)
    return GuardedAnswer(answer=text, citations=valid, answerable=True)
