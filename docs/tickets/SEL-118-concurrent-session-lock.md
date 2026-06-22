# SEL-118 — Define the concurrent-request contract for a session

| | |
|---|---|
| **Type** | Tech-debt |
| **Area** | chat/api |
| **Priority** | Low |
| **Status** | Open |

## Context

Two simultaneous `POST /chat` with the same `session_id` (double-click, retry) read the same
checkpoint; last-writer-wins and one turn silently vanishes — looks like "the bot forgot".

## Proposed work

- Document the contract: the frontend serializes turns (disable input while a reply is pending).
- If it bites: add a per-`session_id` in-process lock or an optimistic version check on the
  checkpoint.

## Why it matters

Silent turn loss is confusing; cheap to document now, harden later only if needed.

**Source:** docs/idee.md §P · **Touches:** `app/api/chat.py`, `app/chat/checkpointer.py`
