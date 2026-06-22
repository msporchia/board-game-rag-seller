# SEL-105 — Compute a per-game quality score and gate on it

| | |
|---|---|
| **Type** | Feature |
| **Area** | ingestion/enricher |
| **Priority** | Medium |
| **Status** | Open |

## Context

Every game enters Qdrant equally, including poorly-described ones with no web coverage — they
add noise to the top-K. We already hold the signals to judge quality (residual `missing_info`,
web-judge pass rate, presence of structured fields).

## Proposed work

- Derive `enriched.quality_score` (0–1) from those signals.
- Use it to: trigger a stricter re-prompt, flag low quality in the payload for downstream
  filtering, or queue manual re-enrichment.

## Why it matters

Lets retrieval down-weight or quarantine weak records instead of polluting results.

**Source:** docs/idee.md §G + docs/note.md · **Touches:** `app/models/game_data.py`, `app/ingestion/enricher/`, `app/ingestion/serializer.py`
