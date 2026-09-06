"""Runtime guardrails, kept separate from the RAG core.

    input          check_input()        — before retrieval / generation
    output         check_output()       — after generation, before the answer is returned
    authorization  retrieval_context()  — the retrieval authorization boundary

The RAG pipeline (retrieval, rerank, abstention, generation) is untouched; these
wrap it. Faithfulness/citation *evaluation* lives in ``evaluation/`` and is not
duplicated here — the runtime grounding check only catches obvious failures.
"""

from src.guardrails.authorization import (
    RetrievalContext,
    retrieval_context,
    where_filter,
)
from src.guardrails.input import check_input
from src.guardrails.output import GuardedAnswer, check_output

__all__ = [
    "check_input",
    "check_output",
    "GuardedAnswer",
    "retrieval_context",
    "where_filter",
    "RetrievalContext",
]
