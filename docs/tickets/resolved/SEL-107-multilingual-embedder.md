# SEL-107 — Evaluate a multilingual embedder (bge-m3 / multilingual-e5)

| | |
|---|---|
| **Type** | Feature / Eval |
| **Area** | rag/retrieval |
| **Priority** | High |
| **Status** | Resolved (2026-07-03) — bge-m3 adopted as default |

## Context

`nomic-embed-text` is EN-centric and weak on Italian terms — it returns a flat similarity band
that does not separate mechanic axes like *cooperativo* (see SEL-142). It's a parallel lever to
the structured-signal fix, not a substitute.

## Proposed work

- Swap in `bge-m3` (1024d) or `multilingual-e5-large`, recreate the Qdrant collection.
- Re-baseline `tests/eval/GameRetriever` and compare NDCG / recall before vs after.

## Why it matters

Italian-heavy queries sit at low recall today; a stronger embedder is expected to lift several
points without touching the pipeline.

## Resolution (2026-07-03)

Measured `bge-m3` against `nomic-embed-text` on the two frozen rulers, same corpus, same qrels
(full protocol and per-query detail in [`docs/experiments.md`](../../experiments.md) rows 1-2):

| Ruler | nomic | bge-m3 |
|-------|-------|--------|
| Suite `core` (12 queries × 50 games, raw `rule` text) | R@5 0.25 · P@5 0.40 · err 0.32 | **R@5 0.43 · P@5 0.67 · err 0.20** |
| Ranking NDCG (frozen enriched corpus) | mean 0.386 · 0/12 perfect | **mean 0.701** · displacement 10.68 → 3.51 |

Biggest single lever measured on the project so far (+72% recall). Worst Italian-theme queries
unblocked: «mondo antico, Grecia o Roma» 1st-relevant #11 → **#1**; `treni-famiglia` NDCG
0.00 → **1.00**. The hypothesis was confirmed exactly as stated: parallel lever, not a
substitute — `coop-famiglia-figli` moved only 0.13 → 0.21 (mechanic axis still needs the
SEL-142 structured filter, whose flag is pending backfill on the live store).

Adopted: default flipped to `bge-m3` (`app/config.py`, `docker-compose.yml`, `.env.example`)
and the live `games` collection re-embedded from the stored `embed_text`s (501 products, no
LLM re-run). `multilingual-e5-large` was not tried: the first candidate cleared the bar by a
margin that made a second candidate a diminishing return; re-opening it stays cheap (same
rulers, ~1 min of eval).

**Source:** docs/idee.md §C + docs/valutazione.md §6 · **Related:** SEL-142 · **Touches:** `app/config.py`, `app/core/vector_store.py`
