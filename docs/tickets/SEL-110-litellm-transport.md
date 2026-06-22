# SEL-110 — Move LLM transport behind LiteLLM (provider-agnostic)

| | |
|---|---|
| **Type** | Refactor |
| **Area** | ingestion/enricher + chat |
| **Priority** | Low (must-have before cloud) |
| **Status** | Open |

## Context

`ChatOllama` is hard-wired throughout. Testing Haiku/Sonnet or moving to the cloud currently
means touching transport in every step.

## Proposed work

- Introduce LiteLLM's OpenAI-compatible client as the single transport seam.
- Switch models by config string (`ollama/llama3.1` → `anthropic/claude-haiku-4-5`) with no
  business-logic changes.

## Why it matters

A structural seam to build before it's urgent, so the cloud move is a config change, not a
refactor.

**Source:** docs/idee.md §E · **Touches:** `app/ingestion/enricher/curator.py`, `app/ingestion/enricher/web.py`, `app/chat/piloted.py`
