"""Offline tests for the non-judge metrics and the answerable/unanswerable split.

Evaluators return a list: ``[Evaluation]`` when the metric applies, ``[]`` when it
does not.
"""

import pytest

from evaluation import metrics

PTO, HOL = "pto-and-leave-policy", "holiday-schedule"
ANSWERABLE = {"answer": "5 days", "sources": [PTO]}
UNANSWERABLE = {"answer": "I don't know.", "sources": []}


def _out(sources, answer="x"):
    return {"sources": sources, "answer": answer, "contexts": ["c"]}


def _value(evals):
    return evals[0].value if evals else None


# --- retrieval: single relevant doc --------------------------------------

@pytest.mark.parametrize(
    "sources, hit",
    [
        ([f"{PTO}.pdf", "benefits-overview.pdf"], True),
        (["benefits-overview.pdf"], False),
        (["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf", f"{PTO}.pdf"], False),  # rank 6
    ],
)
def test_hit_at_5(sources, hit):
    assert _value(metrics.hit_at_5(output=_out(sources), expected_output=ANSWERABLE)) is hit


# --- retrieval: multi relevant doc ------------------------------------

def test_recall_at_5_fraction():
    exp = {"answer": "x", "sources": [PTO, HOL]}
    assert _value(metrics.recall_at_5(output=_out([f"{PTO}.pdf"]), expected_output=exp)) == 0.5
    assert _value(metrics.recall_at_5(output=_out([f"{PTO}.pdf", f"{HOL}.pdf"]), expected_output=exp)) == 1.0
    assert _value(metrics.recall_at_5(output=_out(["x.pdf"]), expected_output=exp)) == 0.0


def test_mrr():
    assert _value(metrics.mrr(output=_out([f"{PTO}.pdf"]), expected_output=ANSWERABLE)) == 1.0
    assert _value(metrics.mrr(output=_out(["a.pdf", "b.pdf", f"{PTO}.pdf"]), expected_output=ANSWERABLE)) == pytest.approx(0.333)
    assert _value(metrics.mrr(output=_out(["a.pdf"]), expected_output=ANSWERABLE)) == 0.0


# --- answerable / unanswerable split -------------------------------

def test_retrieval_metrics_skip_unanswerable():
    for fn in (metrics.hit_at_5, metrics.recall_at_5, metrics.mrr, metrics.citation):
        assert fn(output=_out(["a.pdf"]), expected_output=UNANSWERABLE) == []


def test_abstention_skips_answerable():
    # the unanswerable branch calls the judge model, so only the skip is unit-tested
    assert metrics.abstention(output=_out([], "x"), expected_output=ANSWERABLE) == []


def test_faithfulness_correctness_skip_unanswerable():
    for fn in (metrics.faithfulness, metrics.correctness):
        assert fn(output=_out([], "x"), expected_output=UNANSWERABLE) == []


# --- claim-decomposition parsing (judge I/O mocked out) --------------

def test_strip_citations():
    assert metrics._strip_citations(
        "The budget is $2,000 [benefits-overview.pdf, Page: 4, Heading: 8.1]."
    ) == "The budget is $2,000."
    assert metrics._strip_citations("No citation here.") == "No citation here."
    assert metrics._strip_citations("[a] and [b] cited") == " and cited"


def test_parse_claims_strips_numbering_and_blanks():
    text = "1. Offices close Dec 26-31\n2) Days are paid\n- extra bullet\n\n   \n3. Not deducted from PTO"
    assert metrics._parse_claims(text) == [
        "Offices close Dec 26-31",
        "Days are paid",
        "extra bullet",
        "Not deducted from PTO",
    ]


@pytest.mark.parametrize(
    "reply, total, score",
    [
        ("1. YES\n2. YES\n3. NO\n4. YES", 4, 0.75),
        ("1. NO\n2. NO", 2, 0.0),
        ("all three: YES, YES, YES", 3, 1.0),
        ("YES YES YES", 2, 1.0),   # capped
        ("", 0, 1.0),              # nothing to verify
    ],
)
def test_yes_fraction(reply, total, score):
    assert metrics._yes_fraction(reply, total) == score


@pytest.mark.parametrize(
    "reply, score",
    [("85", 0.85), ("Score: 90", 0.9), ("100 / 100", 1.0), ("120", 1.0), ("n/a", 0.0)],
)
def test_parse_rating(reply, score):
    assert metrics._parse_rating(reply) == score


# --- attribution: fraction of expected sources cited ------------------

@pytest.mark.parametrize(
    "answer, expected_sources, score",
    [
        (f"5 days [{PTO}]", [PTO], 1.0),
        (f"5 days [{PTO}.pdf, Page 1]", [PTO], 1.0),
        ("5 days [pto‑and‑leave‑policy]", [PTO], 1.0),  # non-breaking hyphens
        ("5 days, no citation", [PTO], 0.0),
        (f"[{PTO}] and [{HOL}]", [PTO, HOL], 1.0),
        (f"only [{PTO}] here", [PTO, HOL], 0.5),  # multi-hop, one source cited
    ],
)
def test_citation(answer, expected_sources, score):
    exp = {"answer": "x", "sources": expected_sources}
    assert _value(metrics.citation(output=_out([], answer), expected_output=exp)) == score


# --- E2E composite (generation scores must clear PASS_THRESHOLD) ------

class _Score:
    def __init__(self, name, value):
        self.name, self.value = name, value


@pytest.mark.parametrize(
    "hit, faithful, correct, success",
    [
        (True, 1.0, 1.0, True),
        (True, 0.7, 0.9, True),    # at/above PASS_THRESHOLD
        (True, 0.5, 1.0, False),   # below
        (True, 1.0, 0.5, False),
        (False, 1.0, 1.0, False),
    ],
)
def test_task_success_answerable(hit, faithful, correct, success):
    evals = [_Score("hit@5", hit), _Score("faithfulness", faithful), _Score("correctness", correct)]
    assert _value(metrics.task_success(expected_output=ANSWERABLE, evaluations=evals)) is success


@pytest.mark.parametrize("abstained", [True, False])
def test_task_success_unanswerable(abstained):
    evals = [_Score("abstention", abstained)]
    assert _value(metrics.task_success(expected_output=UNANSWERABLE, evaluations=evals)) is abstained
