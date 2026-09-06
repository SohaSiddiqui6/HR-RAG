"""Output guardrails: empty / length / citations / grounding / secrets / schema."""

from src.guardrails.output import (
    MAX_ANSWER_CHARS,
    GuardedAnswer,
    check_output,
    grounding_ratio,
    redact_secrets,
    validate_citations,
)

SOURCES = [{"source": "pto-and-leave-policy.pdf", "page_no": 2, "headings": "Carryover"}]
CONTEXT = ["Full-time staff accrue PTO at 1.5 days per month, carried over up to five days."]


def _guarded(text, *, sources=SOURCES, contexts=CONTEXT, abstained=False) -> GuardedAnswer:
    return check_output(text, sources=sources, contexts=contexts, abstained=abstained)


# --- empty / structure ---------------------------------------------------

def test_empty_output_returns_a_safe_fallback():
    result = _guarded("   ")
    assert isinstance(result, GuardedAnswer)
    assert not result.answerable
    assert result.answer and "try" in result.answer.lower()


def test_result_always_matches_the_schema():
    result = _guarded("Staff accrue 1.5 days per month [pto-and-leave-policy].")
    assert isinstance(result.answer, str)
    assert isinstance(result.citations, list)
    assert isinstance(result.answerable, bool)


# --- length ------------------------------------------------------------

def test_output_over_the_hard_limit_is_capped():
    result = _guarded("word " * 2000, contexts=["word"])
    assert len(result.answer) <= MAX_ANSWER_CHARS


# --- citations -------------------------------------------------------

def test_valid_citation_is_kept():
    text, valid, fabricated = validate_citations(
        "Carryover is capped at five days [pto-and-leave-policy].", SOURCES
    )
    assert valid == ["pto-and-leave-policy"]
    assert fabricated == []
    assert "[pto-and-leave-policy]" in text


def test_verbose_citation_with_page_and_heading_is_kept():
    text, valid, fabricated = validate_citations(
        "Not reimbursable [expense-reimbursement-policy.pdf, Page: 5, Heading: 11. "
        "Non-Reimbursable Expenses].",
        [{"source": "expense-reimbursement-policy.pdf"}],
    )
    assert valid == ["expense-reimbursement-policy"]
    assert fabricated == []
    assert "[expense-reimbursement-policy.pdf, Page: 5" in text


def test_answer_without_a_citation_is_left_alone():
    text, valid, fabricated = validate_citations("Carryover is capped at five days.", SOURCES)
    assert valid == [] and fabricated == []
    assert text == "Carryover is capped at five days."


def test_fabricated_citation_is_stripped():
    text, valid, fabricated = validate_citations(
        "Bonuses are paid quarterly [compensation-policy].", SOURCES
    )
    assert fabricated == ["compensation-policy"]
    assert "[compensation-policy]" not in text


def test_citation_to_a_non_retrieved_chunk_is_stripped():
    text, valid, fabricated = validate_citations(
        "See [pto-and-leave-policy] and [handbook-2024].", SOURCES
    )
    assert valid == ["pto-and-leave-policy"]
    assert fabricated == ["handbook-2024"]
    assert "handbook-2024" not in text


def test_generic_brackets_are_not_treated_as_citations():
    _, valid, fabricated = validate_citations("The answer is [redacted].", SOURCES)
    assert valid == [] and fabricated == ["redacted"]


# --- grounding -----------------------------------------------------

def test_obviously_ungrounded_answer_is_replaced():
    result = _guarded("The mitochondria is the powerhouse of the cell.")
    assert not result.answerable
    assert "enough information" in result.answer.lower()


def test_grounded_answer_passes():
    result = _guarded("Full-time staff accrue PTO at 1.5 days per month [pto-and-leave-policy].")
    assert result.answerable
    assert grounding_ratio(result.answer, CONTEXT) >= 0.15


# --- secrets ---------------------------------------------------------

def test_api_key_and_token_are_redacted():
    text = redact_secrets(
        "Use key sk-abcdef0123456789abcdef0123 and token ghp_" + "a" * 36
    )
    assert "sk-abcdef" not in text
    assert "ghp_" not in text


def test_password_assignment_is_redacted():
    assert "hunter2" not in redact_secrets("The password: hunter2xx is shared")


def test_company_email_is_not_redacted():
    text = redact_secrets("Contact the HR team at hr@company.com for details.")
    assert "hr@company.com" in text


# --- abstention passthrough --------------------------------------

def test_abstention_is_passed_through_untouched():
    result = check_output(
        "I don't have information about that in the available HR policies.",
        sources=[],
        contexts=[],
        abstained=True,
    )
    assert not result.answerable
    assert result.answer.startswith("I don't have information")
