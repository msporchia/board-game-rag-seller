# SEL-104 — Enforce structured LLM output with validated retry

| | |
|---|---|
| **Type** | Feature |
| **Area** | ingestion/enricher |
| **Priority** | High |
| **Status** | Open |

## Context

Enricher steps parse model output with `format="json"` + `json.loads()` + `try/except`. With a
local 8B model a malformed JSON is a silent failure: a lost batch and a missing label.

## Proposed work

- Replace the ad-hoc parse with a schema-enforcing path (Pydantic `with_structured_output`,
  Instructor for validated retry, or Outlines for generation-level constraint).
- Apply across Curator and Web enrichers.

## Why it matters

Eliminates a whole class of silent data-loss failures by construction or by retry.

**Source:** docs/idee.md §A · **Touches:** `app/ingestion/enricher/curator.py`, `app/ingestion/enricher/web.py`
