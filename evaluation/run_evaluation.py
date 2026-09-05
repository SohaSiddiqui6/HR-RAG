"""Offline evaluation over the golden set in eval_questions.json.

For each question it runs the full RAG chain and scores two things:

- citation accuracy - was the expected source document cited in the answer?
- groundedness      - LLM-as-judge: is every claim supported by the retrieved context?

Plus latency percentiles. Results are written to evaluation/eval_results.json.

    python -m evaluation.run_evaluation
"""

from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.rag_chain import answer_question

QUESTIONS_FILE = Path(__file__).parent / "eval_questions.json"
RESULTS_FILE = Path(__file__).parent / "eval_results.json"

judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=10)

JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an impartial judge evaluating whether an answer is fully "
                "supported by the provided context. Respond with ONLY 'GROUNDED' or "
                "'NOT_GROUNDED'. If the answer correctly says it cannot find the "
                "information, that is GROUNDED. Minor paraphrasing is acceptable."
            ),
        ),
        (
            "human",
            (
                "Context:\n{context}\n\nQuestion: {question}\n\nAnswer: {answer}\n\n"
                "Is this answer fully grounded in the context?"
            ),
        ),
    ]
)


def source_stem(value: str | None) -> str:
    return Path(str(value or "")).stem


def citation_accurate(answer: str, expected_source: str) -> bool:
    """Was the expected source cited, in any of the bracket formats models use?"""
    normalised = (
        answer.replace("‑", "-").replace("–", "-").replace("—", "-")
    )
    for item in re.findall(r"\[([^\]]+)\]", normalised):
        item = re.sub(r"^Source\s+\d+:\s*", "", item, flags=re.IGNORECASE).strip()
        if item == expected_source or source_stem(item) == expected_source:
            return True
    return False


def is_grounded(question: str, answer: str, contexts: list[str]) -> bool:
    response = (JUDGE_PROMPT | judge_llm).invoke(
        {"context": "\n\n".join(contexts), "question": question, "answer": answer}
    )
    verdict = response.content.upper()
    return "GROUNDED" in verdict and "NOT_GROUNDED" not in verdict


def main() -> None:
    cases = json.loads(QUESTIONS_FILE.read_text())
    results: list[dict] = []
    latencies: list[int] = []

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['question']}")

        start = time.time()
        answer = answer_question(case["question"])
        latency_ms = round((time.time() - start) * 1000)
        latencies.append(latency_ms)

        cite = citation_accurate(answer.text, case["expected_source"])
        time.sleep(1)  # be gentle with the judge model's rate limit
        grounded = is_grounded(case["question"], answer.text, answer.contexts)

        results.append(
            {
                "id": case["id"],
                "domain": case.get("domain"),
                "question": case["question"],
                "expected_source": case["expected_source"],
                "answer": answer.text,
                "sources": [s["source"] for s in answer.sources],
                "citation_accurate": cite,
                "grounded": grounded,
                "latency_ms": latency_ms,
            }
        )
        print(f"  grounded={grounded}  citation={cite}  {latency_ms}ms")

    n = len(results)
    metrics = {
        "total_questions": n,
        "groundedness_pct": round(sum(r["grounded"] for r in results) / n * 100, 1),
        "citation_accuracy_pct": round(
            sum(r["citation_accurate"] for r in results) / n * 100, 1
        ),
        "latency_p50_ms": round(statistics.median(latencies)),
        "latency_p95_ms": sorted(latencies)[min(n - 1, int(n * 0.95))],
        "latency_mean_ms": round(statistics.mean(latencies)),
    }

    RESULTS_FILE.write_text(json.dumps({"metrics": metrics, "results": results}, indent=2))

    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    for key, value in metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
