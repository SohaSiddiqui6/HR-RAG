# Evaluation

```
        dataset.json — 30 items (24 answerable, 6 unanswerable)
                   │
        langfuse.run_experiment
                   │
      ┌────────────┼────────────────────┐
   Retrieval    Generation              E2E
   hit@5      faithfulness   answerable → task_success = hit@5 ∧ faithful ∧ correct
   recall@5   correctness    unanswerable → task_success = abstention
   mrr        citation
                   │
             find failures ──► paste into dataset.json with "regression" tag
                   │
        run_evaluation --tag regression   (expect task_success 1.0)
```

## Dataset

Each item: `question`, `expected_answer`, `expected_sources`, `tags`.

- **`expected_sources`** — list of relevant document stems. **Empty ⇒ the question
  is unanswerable** from the knowledge base; the RAG should decline.
- **`tags`** — used for filtering (`--tag …`) *and* as the question category. Every
  item has `golden` plus one of `factual` / `conceptual` / `comparison` /
  `multi-hop` / `unanswerable`. Regression items add `regression`.

## Metrics

| metric | applies to | range | how |
|---|---|---|---|
| `hit@5` | answerable | 0/1 | ≥1 relevant doc in the top 5 retrieved chunks |
| `recall@5` | answerable | 0–1 | fraction of relevant docs in the top 5 (matters for multi-hop) |
| `mrr` | answerable | 0–1 | reciprocal rank of the first relevant doc |
| `faithfulness` | answerable | 0–1 | fraction of the answer's claims supported by the retrieved context (claim decomposition, 2 judge calls) |
| `correctness` | answerable | 0–1 | fraction of the reference answer's facts covered by the answer (claim decomposition, 2 judge calls) |
| `citation` | answerable | 0–1 | fraction of expected sources that appear in a `[...]` bracket |
| `abstention` | unanswerable | 0/1 | LLM judge: the answer declines (system abstains when no chunk clears `RELEVANCE_THRESHOLD`) |
| `task_success` | all | 0/1 | pass/fail: `hit@5` + `faithfulness` & `correctness` ≥ `PASS_THRESHOLD` (0.7), or `abstention` |
| latency / cost / tokens / errors | all | | Langfuse traces |

Definitions live in [metrics.py](metrics.py); non-applicable metrics return `[]`,
so each aggregate is the mean over the items that emitted it (an average graded
score for the judge metrics, a pass rate for `task_success`).

## Run

```bash
uv run python -m evaluation.run_evaluation                  # whole dataset
uv run python -m evaluation.run_evaluation --limit 5        # smoke run
uv run python -m evaluation.run_evaluation --tag unanswerable
uv run python -m evaluation.run_evaluation --tag regression
```

Needs `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (see [../.env.example](../.env.example)).
Writes `results.json` (aggregate + per-tag `task_success` + per-item scores);
traces and run comparison are in the Langfuse UI.
