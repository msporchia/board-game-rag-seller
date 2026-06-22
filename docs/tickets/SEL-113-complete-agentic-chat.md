# SEL-113 — Harden the agentic (tool-calling) chat engine

| | |
|---|---|
| **Type** | Feature |
| **Area** | chat/agent |
| **Priority** | Medium |
| **Status** | Open (experimental) |

## Context

`AgenticChat` + `SearchCatalogTool` run end-to-end on a strong model (qwen2.5:7b) but the arm is
still experimental: no scored eval gate, no session-history state, no circuit breaker, no A/B
hookup.

## Proposed work

- Add a scored `ChatConversation` run with `engine=agent`.
- Wire session history, a search-budget circuit breaker, and arm reporting.

## Why it matters

The agent is the primary slot in `TieredChat` and fixes the re-retrieval / paraphrase-mismatch
gap better than weak-model prompting — but it needs a gate before it can be trusted.

**Source:** docs/idee.md §Q + docs/stato.md · **Touches:** `app/chat/agentic.py`, `app/chat/tools/`, `tests/eval/ChatConversation/`
