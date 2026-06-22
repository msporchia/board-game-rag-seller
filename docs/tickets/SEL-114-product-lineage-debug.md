# SEL-114 — Product lineage journal + per-game debug endpoint

| | |
|---|---|
| **Type** | Feature |
| **Area** | api / observability |
| **Priority** | High (design to re-discuss) |
| **Status** | Open |

## Context

Three operational blind spots: no run ledger ("how are pipelines doing?"), no per-game history
("what happened to game X?"), and all-or-nothing reprocessing ("how do I retry one product?").

## Proposed work

- `product_events` journal (step / status / duration per game per run) + `pipeline_runs` summary.
- Add `id_product` to traces.
- `GET /debug/games/{id}` assembling the full story (record + events + extractions + LLM calls +
  Qdrant status). Optional `--game <id> --force` retry CLI.

## Why it matters

These are showstoppers for production debugging once the catalog grows.

**Source:** docs/idee.md §M (refactor backlog) · **Touches:** `app/core/enrichment_store.py`, `app/ingestion/ingester.py`, `app/api/`
