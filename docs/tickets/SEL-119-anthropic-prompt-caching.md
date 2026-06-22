# SEL-119 — Anthropic prompt caching for Synth on cloud models

| | |
|---|---|
| **Type** | Feature |
| **Area** | ingestion/enricher + config |
| **Priority** | Medium (deferred to cloud phase) |
| **Status** | Open |

## Context

Once Synth runs on Sonnet/Haiku via the Anthropic API, the stable prompt prefix (system + closed
vocabularies) is re-sent on every game — paying full price for identical tokens.

## Proposed work

- Mark the stable block with `cache_control: {"type": "ephemeral"}` (90% off cached reads).
- Preconditions: stabilized Synth prompt, batch (nightly) ingest to keep the cache warm,
  stable/variable blocks separated in the prompt.

## Why it matters

Estimated ~$700–1k/year saved at 5k games/month; only relevant after the cloud move.

**Source:** docs/note.md §"Anthropic prompt caching" · **Depends on:** SEL-110 · **Touches:** `app/ingestion/enricher/synth.py`, `app/config.py`
