# SEL-149 — Cost & usage dashboard

| | |
|---|---|
| **Type** | Feature (Observability) |
| **Area** | observability + api |
| **Priority** | Medium |
| **Reported** | 2026-07-06 |
| **Status** | Open |

## Context

The `traces` table already records input/output tokens per LLM call
(`app/core/tracing/handler.py`), but nothing **aggregates** them into a spend view. You cannot see
today's cost, spot an abuse spike, or know which engine/model is burning the budget — and SEL-148's
hard-limit needs exactly this material to act on.

## Proposed work

- A read-only view (endpoint and/or simple page): **cost & tokens per day / per engine / per
  model**, request volume, and the top-spending sessions. Cost = tokens × a per-model price table
  (shared with SEL-148).
- Make it the place where an operator notices "requests 10× normal at 3am" before the bill does.

## Why it matters

Visibility is the precondition for the limit (SEL-148) and for the ROI question (SEL-150). It also
fits the showcase: the project already argues quality-per-token (`docs/showcase/chat.md`) — a live
cost view is the operator-facing half of that story.

**Source:** conversation 2026-07-06 (cost priorities) · **Related:** SEL-148 (hard-limit),
SEL-150 (cost per conversion), SEL-101 (Langfuse tracing), SEL-103 (token counts),
SEL-114 (debug endpoint) · **Touches:** `app/core/tracing/`, `app/api/`
