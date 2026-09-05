"""Scoring functions for the RAG evaluation — each returns a list of Langfuse
``Evaluation`` objects (``[]`` when the metric does not apply to that item).

Item evaluators get the task ``output`` (``{"answer", "sources", "contexts"}``)
plus the item's ``input`` / ``expected_output``. An item with no
``expected_output["sources"]`` is *unanswerable*: retrieval + generation metrics
are skipped and ``abstention`` is scored instead. ``task_success`` is a composite
over the item's other evaluations.

``faithfulness`` uses claim decomposition (``_coverage``): the answer is split
into atomic claims and each is verified against the retrieved context, so the
score is a real fraction (3 of 4 claims → 0.75). ``correctness`` uses a single
holistic 0-100 judge (``_rating``) — the answer may be phrased more richly than
the terse reference, which would make claim decomposition misfire.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langfuse import Evaluation

from src import config

_judge = ChatOpenAI(model=config.LLM_MODEL, temperature=0)

_CLAIMS = (
    "Break the text below into a numbered list of atomic factual claims, one per "
    "line. Keep each claim self-contained. Output only the list."
)

_SUPPORTED = (
    "For each numbered CLAIM output its number and YES if the REFERENCE text "
    "supports it, otherwise NO. One claim per line, nothing else."
)


def _strip_citations(text: str) -> str:
    """Remove inline ``[source, page, heading]`` citation brackets."""
    return re.sub(r"\s*\[[^\]]*\]", "", text)


def _parse_claims(text: str) -> list[str]:
    """Strip list numbering / bullets from each non-empty line."""
    stripped = (re.sub(r"^\s*[\d.)\-]+\s*", "", line).strip() for line in text.splitlines())
    return [c for c in stripped if c]


def _yes_fraction(text: str, total: int) -> float:
    """Fraction of ``total`` claims the verify reply marks YES (capped at 1.0)."""
    if not total:
        return 1.0
    yes = len(re.findall(r"\bYES\b", text.upper()))
    return round(min(yes, total) / total, 3)


def _parse_rating(text: str) -> float:
    """First integer in ``text`` as a 0-1 score (``"85"`` → 0.85), 0.0 if none."""
    match = re.search(r"\d+", text)
    return round(min(int(match.group()), 100) / 100, 3) if match else 0.0


def _claims(passage: str) -> list[str]:
    """Judge call 1 — split ``passage`` into atomic factual claims."""
    reply = _judge.invoke([("system", _CLAIMS), ("human", passage)]).content
    return _parse_claims(str(reply))


def _supported(claims: list[str], reference: str) -> float:
    """Judge call 2 — fraction of ``claims`` the ``reference`` text supports."""
    if not claims:
        return 1.0
    listed = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))
    reply = _judge.invoke(
        [("system", _SUPPORTED), ("human", f"REFERENCE:\n{reference}\n\nCLAIMS:\n{listed}")]
    ).content
    return _yes_fraction(str(reply), len(claims))


def _coverage(answer: str, reference: str) -> float:
    """Fraction of the answer's atomic claims that ``reference`` supports.

    Two judge calls (decompose, then verify) — an honest fraction (3 of 4 = 0.75),
    not a coarse yes/partial/no. Citations are stripped so ``[source, page]`` text
    isn't scored as a claim.
    """
    return _supported(_claims(_strip_citations(answer)), reference)


def _verdict(criterion: str, user: str) -> bool:
    """Ask the judge a yes/no question; True on 'YES'."""
    system = f"{criterion} Reply with only YES or NO."
    reply = _judge.invoke([("system", system), ("human", user)]).content
    return "YES" in str(reply).upper()


def _rating(criterion: str, user: str) -> float:
    """One judge call, 0-1. Asks for 0-100 and parses the first number.

    Used where the answer can legitimately be phrased more richly than the
    reference, so claim decomposition would misfire.
    """
    system = f"{criterion} Reply with only a whole number from 0 to 100."
    reply = str(_judge.invoke([("system", system), ("human", user)]).content)
    return _parse_rating(reply)


def _answerable(expected_output) -> bool:
    return bool(expected_output["sources"])


def _stems(sources: list[str], k: int | None = None) -> set[str]:
    return {Path(s).stem for s in (sources[:k] if k else sources)}


# --- Retrieval (answerable only) ------------------------------------------

def hit_at_5(*, output, expected_output, **_) -> list[Evaluation]:
    """Was at least one relevant document in the top 5 retrieved chunks?"""
    if not _answerable(expected_output):
        return []
    relevant = set(expected_output["sources"])
    hit = bool(relevant & _stems(output["sources"], 5))
    return [Evaluation(name="hit@5", value=hit, data_type="BOOLEAN")]


def recall_at_5(*, output, expected_output, **_) -> list[Evaluation]:
    """Fraction of relevant documents that appear in the top 5 retrieved chunks."""
    if not _answerable(expected_output):
        return []
    relevant = set(expected_output["sources"])
    found = relevant & _stems(output["sources"], 5)
    return [Evaluation(name="recall@5", value=round(len(found) / len(relevant), 3), data_type="NUMERIC")]


def mrr(*, output, expected_output, **_) -> list[Evaluation]:
    """Reciprocal rank of the first relevant document in the retrieved list."""
    if not _answerable(expected_output):
        return []
    relevant = set(expected_output["sources"])
    ranks = [i for i, s in enumerate(output["sources"], 1) if Path(s).stem in relevant]
    return [Evaluation(name="mrr", value=round(1 / ranks[0], 3) if ranks else 0.0, data_type="NUMERIC")]


# --- Generation ------------------------------------------------------------

_CORRECT = (
    "Rate how correct and complete the ANSWER is compared with the REFERENCE "
    "answer to the QUESTION. Extra detail that is consistent with the reference "
    "is fine; missing or contradicting information lowers the score."
)

_ABSTAINED = (
    "You check whether the ANSWER declines to answer — e.g. says it does not "
    "know or that the information is not in the provided policies."
)


def faithfulness(*, output, expected_output, **_) -> list[Evaluation]:
    """Fraction of the answer's claims supported by the retrieved context. (answerable only)"""
    if not _answerable(expected_output):
        return []
    context = "\n\n".join(output["contexts"])
    return [Evaluation(name="faithfulness", value=_coverage(output["answer"], context), data_type="NUMERIC")]


def correctness(*, output, expected_output, input=None, **_) -> list[Evaluation]:
    """How correct the answer is vs the reference — holistic 0-1 judge. (answerable only)"""
    if not _answerable(expected_output):
        return []
    question = (input or {}).get("question", "")
    user = (
        f"QUESTION: {question}\n\n"
        f"REFERENCE: {expected_output['answer']}\n\n"
        f"ANSWER: {output['answer']}"
    )
    return [Evaluation(name="correctness", value=_rating(_CORRECT, user), data_type="NUMERIC")]


def abstention(*, output, expected_output, **_) -> list[Evaluation]:
    """Did the answer correctly decline? (unanswerable items only)"""
    if _answerable(expected_output):
        return []
    return [Evaluation(name="abstention", value=_verdict(_ABSTAINED, output["answer"]), data_type="BOOLEAN")]


# --- Attribution (answerable only) --------------------------------------

def citation(*, output, expected_output, **_) -> list[Evaluation]:
    """Fraction of expected sources named inside a [...] citation bracket. (answerable only)"""
    if not _answerable(expected_output):
        return []
    text = output["answer"].replace("‑", "-").replace("–", "-").replace("—", "-")
    brackets = [b.replace(".pdf", "") for b in re.findall(r"\[([^\]]+)\]", text)]
    expected = expected_output["sources"]
    cited = sum(any(src in b for b in brackets) for src in expected) / len(expected)
    return [Evaluation(name="citation", value=round(cited, 3), data_type="NUMERIC")]


# --- E2E -------------------------------------------------------------------

PASS_THRESHOLD = 0.7  # min faithfulness / correctness for an answerable item to pass


def task_success(*, expected_output, evaluations, **_) -> list[Evaluation]:
    """Composite pass/fail. Answerable: evidence retrieved and both generation
    scores at or above ``PASS_THRESHOLD``. Unanswerable: correctly abstained."""
    scores = {e.name: e.value for e in evaluations}
    if _answerable(expected_output):
        ok = (
            bool(scores.get("hit@5"))
            and (scores.get("faithfulness") or 0) >= PASS_THRESHOLD
            and (scores.get("correctness") or 0) >= PASS_THRESHOLD
        )
    else:
        ok = bool(scores.get("abstention"))
    return [Evaluation(name="task_success", value=ok, data_type="BOOLEAN")]
