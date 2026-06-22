# SEL-107 — Evaluate a multilingual embedder (bge-m3 / multilingual-e5)

| | |
|---|---|
| **Type** | Feature / Eval |
| **Area** | rag/retrieval |
| **Priority** | High |
| **Status** | Open |

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

**Source:** docs/idee.md §C + docs/valutazione.md §6 · **Related:** SEL-142 · **Touches:** `app/config.py`, `app/core/vector_store.py`
