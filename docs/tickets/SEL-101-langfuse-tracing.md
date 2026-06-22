# SEL-101 — Wire Langfuse tracing into the running stack

| | |
|---|---|
| **Type** | Tech-debt / Feature |
| **Area** | observability/tracing |
| **Priority** | High |
| **Status** | Open |

## Context

A tracing stub exists (`app/core/tracing/`) but is not deployed or wired to production runs.
Debugging an enricher failure today means manual log archaeology.

## Proposed work

- Add self-hosted Langfuse to `docker-compose.yml`.
- Wire the callback handler so each LLM call records prompt / output / latency on a timeline.
- Lay the groundwork for LLM-as-judge evals.

## Why it matters

Diagnosis goes from minutes to seconds, and the upcoming chat tier-routing is undebuggable
without per-call traces.

**Source:** docs/idee.md §B · **Touches:** `app/core/tracing/callbacks.py`, `docker-compose.yml`
