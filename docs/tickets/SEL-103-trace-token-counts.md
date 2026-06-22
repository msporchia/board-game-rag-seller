# SEL-103 — Aggregate token counts into eval reports for cost attribution

| | |
|---|---|
| **Type** | Feature |
| **Area** | observability/tracing |
| **Priority** | Medium |
| **Status** | Open |

## Context

The `traces` table already records `prompt_eval_count` / `eval_count` from Ollama, but the
numbers never reach the eval reports. ChatConversation has no cost denominator today.

## Proposed work

- Add token columns to the trace schema (if missing) and persist them per call.
- Aggregate cost-per-conversation and per-engine (pipeline / piloted / agent) in the report.

## Why it matters

Scoring the tiered chat engine needs a Δquality / Δcost trade-off; without a cost denominator
the arms can't be compared.

**Source:** docs/idee.md §Q · **Touches:** `app/core/tracing/schema.py`, `tests/eval/ChatConversation/report.py`
