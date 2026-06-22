# SEL-106 — Cache Web enricher LLM extractions, not just fetches

| | |
|---|---|
| **Type** | Refactor |
| **Area** | ingestion/enricher |
| **Priority** | Medium |
| **Status** | Open |

## Context

`EnrichmentStore` caches fetched web pages but not the LLM extraction over them. A second ingest
of an unchanged game re-runs identical extraction calls.

## Proposed work

- Add an `extractions` cache keyed by `(game, url, missing, model)`.
- Skip the LLM call on a cache hit.

## Why it matters

Full idempotency: re-run time for unchanged games drops to near zero and redundant LLM spend
disappears.

**Source:** docs/idee.md §J · **Touches:** `app/core/enrichment_store.py`, `app/ingestion/enricher/web.py`
