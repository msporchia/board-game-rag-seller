# SEL-115 — Make TieredChat failover checkpoint-transactional

| | |
|---|---|
| **Type** | Bug |
| **Area** | chat/tiered |
| **Priority** | Medium |
| **Status** | Open (known limitation) |

## Context

The `TieredChat` fallback is not transactional. If the primary engine writes a checkpoint (e.g.
piloted's `_intent`) then raises, the fallback resumes on a dirty checkpoint → duplicated history.
Looks to the user like "the bot forgot".

## Proposed work

- Snapshot the checkpoint before the primary runs; restore it on exception before the fallback
  (all-or-nothing per turn).
- Document the contract and add a unit test for interleaved turns.

## Why it matters

Failover should be transparent; today it can silently corrupt session history.

**Source:** docs/idee.md §Q · **Touches:** `app/chat/tiered.py`, `app/chat/checkpointer.py`
