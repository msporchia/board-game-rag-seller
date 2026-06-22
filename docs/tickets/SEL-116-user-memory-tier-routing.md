# SEL-116 — User memory + Haiku→Sonnet tier routing

| | |
|---|---|
| **Type** | Feature |
| **Area** | chat/state |
| **Priority** | Medium (future scope) |
| **Status** | Open |

## Context

The chat is stateless across sessions and runs a single model tier. The middleware seam
(`custom_policy`) exists, but there's no user profile and no confidence-based escalation.

## Proposed work

- Store a user profile (preferred players, loves/hates, past games, skill level) — likely a
  Qdrant collection.
- Route tiers: a cheap model handles the turn and emits an `escalate` confidence; escalate the
  final recommendation to a stronger model when warranted. Compress session history.

## Why it matters

Strategy selection + escalation is the lever for conversion; the next scope jump beyond ingest.

**Source:** docs/idee.md §L + docs/note.md · **Depends on:** SEL-101, SEL-110 · **Touches:** `app/chat/state.py`, `app/chat/routing.py`
