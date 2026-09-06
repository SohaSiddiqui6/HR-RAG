"""Run the RAG evaluation as a Langfuse experiment.

    python -m evaluation.run_evaluation                  # whole dataset
    python -m evaluation.run_evaluation --tag regression # only regression items
    python -m evaluation.run_evaluation --limit 5        # first 5 (smoke run)

Per item it scores hit@5, recall@5, mrr, faithfulness, correctness, citation,
abstention and the task_success composite (see evaluation/metrics.py) — retrieval
and generation metrics are skipped for unanswerable items (empty
``expected_sources``), which are scored on abstention instead. Latency / cost /
token usage / full traces live in the Langfuse UI. A summary is written to
evaluation/results.json and failing items are printed ready to paste into
dataset.json.

Requires LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (see .env.example).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

from langfuse import Evaluation, get_client
from langfuse.experiment import LocalExperimentItem

from evaluation import metrics
from src.rag.chain import answer_question
from src.tracing import trace_config

DATASET = Path(__file__).parent / "dataset.json"
RESULTS = Path(__file__).parent / "results.json"

ITEM_METRICS = [
    "hit@5",
    "recall@5",
    "mrr",
    "faithfulness",
    "correctness",
    "citation",
    "abstention",
    "task_success",
]


def load_items(tag: str | None, limit: int | None) -> list[LocalExperimentItem]:
    rows = json.loads(DATASET.read_text())
    if tag:
        rows = [r for r in rows if tag in r.get("tags", [])]
    if limit:
        rows = rows[:limit]
    return [
        LocalExperimentItem(
            input={"question": r["question"]},
            expected_output={"answer": r["expected_answer"], "sources": r["expected_sources"]},
            metadata={"id": r["id"], "tags": r.get("tags", [])},
        )
        for r in rows
    ]


def task(*, item, **_) -> dict:
    started = time.perf_counter()
    answer = answer_question(item["input"]["question"], run_config=trace_config())
    return {
        "answer": answer.text,
        "sources": [s["source"] for s in answer.sources],
        "contexts": answer.contexts,
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def mean_score(metric: str):
    """Run-level aggregate: mean of a metric across the items that emitted it
    (= pass rate for booleans). Emits nothing if no item scored the metric."""

    def _agg(*, item_results, **_) -> list[Evaluation]:
        values = [e.value for r in item_results for e in r.evaluations if e.name == metric]
        if not values:
            return []
        return [Evaluation(name=metric, value=round(sum(values) / len(values), 3))]

    _agg.__name__ = f"{metric}_mean"
    return _agg


def _task_success_by_tag(result) -> dict:
    """task_success rate grouped by dataset tag (factual / multi-hop / unanswerable / ...)."""
    groups: dict[str, list[bool]] = {}
    for r in result.item_results:
        success = next((e.value for e in r.evaluations if e.name == "task_success"), None)
        if success is None:
            continue
        for tag in r.item["metadata"]["tags"]:
            if tag != "golden":
                groups.setdefault(tag, []).append(success)
    return {tag: round(sum(v) / len(v), 3) for tag, v in sorted(groups.items())}


def summarise(result, run_name: str) -> dict:
    items, latencies = [], []
    for r in result.item_results:
        scores = {e.name: e.value for e in r.evaluations}
        errored = r.output is None
        if not errored:
            latencies.append(r.output["latency_ms"])
        items.append(
            {
                "id": r.item["metadata"]["id"],
                "question": r.item["input"]["question"],
                "error": errored,
                "latency_ms": None if errored else r.output["latency_ms"],
                **{m: scores.get(m) for m in ITEM_METRICS},
            }
        )

    aggregate = {e.name: e.value for e in result.run_evaluations}
    aggregate["error_count"] = sum(i["error"] for i in items)
    aggregate["latency_p50_ms"] = round(statistics.median(latencies)) if latencies else None
    aggregate["latency_p95_ms"] = (
        round(statistics.quantiles(latencies, n=20)[-1]) if len(latencies) > 1 else None
    )

    summary = {
        "run_name": run_name,
        "aggregate": aggregate,
        "task_success_by_tag": _task_success_by_tag(result),
        "items": items,
    }
    RESULTS.write_text(json.dumps(summary, indent=2))
    return summary


def failing_items(result) -> list[dict]:
    """Failed items, shaped for pasting into dataset.json (keeps the type tag)."""
    out = []
    for r in result.item_results:
        if any(e.name == "task_success" and e.value for e in r.evaluations):
            continue
        exp = r.item["expected_output"]
        tags = [t for t in r.item["metadata"]["tags"] if t != "golden"]
        out.append(
            {
                "id": r.item["metadata"]["id"],
                "question": r.item["input"]["question"],
                "expected_answer": exp["answer"],
                "expected_sources": exp["sources"],
                "tags": [*tags, "regression"],
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="only run dataset items carrying this tag")
    parser.add_argument("--limit", type=int, help="run only the first N items")
    args = parser.parse_args()

    items = load_items(args.tag, args.limit)
    if not items:
        print(f"No dataset items{f' tagged {args.tag!r}' if args.tag else ''}.")
        return

    run_name = datetime.now().strftime("%Y-%m-%d %H:%M")
    langfuse = get_client()
    result = langfuse.run_experiment(
        name="hr-rag",
        run_name=run_name,
        data=items,
        task=task,
        evaluators=[
            metrics.hit_at_5,
            metrics.recall_at_5,
            metrics.mrr,
            metrics.faithfulness,
            metrics.correctness,
            metrics.citation,
            metrics.abstention,
        ],
        composite_evaluator=metrics.task_success,  # type: ignore[arg-type]  # keyword-only subset of the protocol
        run_evaluators=[mean_score(m) for m in ITEM_METRICS],
        max_concurrency=1,  # Cohere trial key = 10 req/min; retrieve() retries 429s
    )
    langfuse.flush()

    print(result.format())

    summary = summarise(result, run_name)
    if summary["task_success_by_tag"]:
        print("task_success by tag:")
        for tag, rate in summary["task_success_by_tag"].items():
            print(f"  {tag:<14} {rate}")

    failures = failing_items(result)
    if failures:
        print(f"\n{len(failures)} failing item(s) — paste into dataset.json:\n")
        print(json.dumps(failures, indent=2))


if __name__ == "__main__":
    main()
