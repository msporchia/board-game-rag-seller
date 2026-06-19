# 0004 — Measure retrieval by ranking, never by an absolute score

**Status:** Accepted · recorded post-hoc 2026-06-19

## Context

To know whether enrichment ([ADR-0001](0001-enrich-embed-text-over-stronger-embedder.md)) helps, we
need a number we can trust. The tempting one is cosine similarity — call everything above a
threshold a "match", report a percentage. But cosine over these embeddings is **uncalibrated**: a
perfect hit and a wrong one can sit ~0.06 apart, and the absolute value drifts with the corpus. A
"70% match" would be a number that *looks* like confidence and carries none.

## Decision

**Rank, don't score.** Evaluate retrieval by where the right games land relative to the wrong ones,
never by an absolute similarity value. The harness (`tests/eval.py`) reports, on a frozen labeled
corpus:

- **Recall@K** and **Precision@K**;
- **normalized inversions** (`err`) — the fraction of relevant/irrelevant pairs mis-ordered
  (0 = perfect, ≈ 1−AUC): "an irrelevant ranked above a relevant" is the unit of error;
- the rank of the first relevant game.

Two rules hold throughout: **we rank, we don't score**, and **the oracle is never fed to the
system** — the labels are the answer key, an input to the *scorer*, never to the retriever.

## Alternatives considered

- **Similarity threshold / "% match".** Rejected: uncalibrated and corpus-dependent, so the number
  is not comparable across runs or games and quietly invites tuning the threshold to flatter a demo.
- **A single end-to-end pass/fail.** Too coarse to attribute a change: it cannot tell a retrieval
  gain that hides a generation loss (which is why evaluation is split into three levels — unit,
  per-step quality, retrieval scorecard).
- **LLM-as-judge for retrieval.** Adds cost and a second source of noise where a deterministic,
  oracle-based metric is both cheaper and reproducible.

## Consequences

- Numbers are **comparable and reproducible**: the same corpus + same queries make a before/after
  delta meaningful (the basis for every figure in the README), and they regenerate each run so a
  stale figure shows as stale rather than dressed up.
- **Cost:** it requires a maintained frozen corpus and a structured oracle (`games.json` /
  `labels.json` / `queries.json` per suite), and `relevant(query)` is only as good as those labels.
- We deliberately **cannot** quote an absolute "the seller is X% accurate" confidence number — by
  design, because that number would be fiction. We report order, not certainty.
