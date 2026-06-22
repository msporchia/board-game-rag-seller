# SEL-117 — A/B experiment infrastructure (arm assignment + conversion loop)

| | |
|---|---|
| **Type** | Feature |
| **Area** | chat/state + api |
| **Priority** | Medium |
| **Status** | Open |

## Context

Policies and engines are swappable but unmeasurable end-to-end: there's no server-side arm
assignment and no way for the client to report conversion per arm.

## Proposed work

- Server-side arm assignment, sticky per session.
- `ChatResponse` echoes the assigned engine/policies so the client reports them on analytics
  events.
- Two-level OEC: offline (convergence + cost guardrails) and online (conversion per arm).

## Why it matters

The structural seam for policy experiments and future multi-arm routers; without it A/B testing
is impossible.

**Source:** docs/idee.md §O/§Q · **Related:** SEL-103 · **Touches:** `app/chat/state.py`, `app/api/chat.py`, `app/chat/models/customer_context.py`
