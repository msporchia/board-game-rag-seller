"""Scorecard + Baseline — the clear "improved/regressed" signal. One class per module:

- `metrics.GameMetrics`: a single game's serializable metrics.
- `spec.MetricSpec` (+ `METRIC_SPECS`): how each metric compares against the baseline.
- `scorecard.Scorecard`: reduces a `RunResult` to stable metrics via the real retrievers.
- `row.Row` / `comparison.Comparison`: the current-vs-baseline diff.
- `baseline.Baseline`: the reference snapshot versioned on git (`baseline.json`).

Philosophy (regression/golden testing — see README):
  - baseline VERSIONED on git: updated only on purpose (`Baseline.write`), never by hand; git
    history becomes the quality trend over time.
  - tolerances, not equalities: the LLM/embeddings aren't bit-deterministic. The GATE rides on
    ROBUST metrics — recall@K (queries reaching the first screen) and the boolean web_fired —
    while raw ranks are noisy and kept INFORMATIONAL only.
  - gate: a regression beyond tolerance on a "gate" metric fails the suite.
"""
