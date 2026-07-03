# Backlog

Lightweight ticket log for the seller (board-game RAG) service. One file per ticket,
`SEL-NNN-slug.md`. Customer-reported bugs are written in plain language; the rest are
engineering tickets. Most items are distilled from `docs/idee.md`, `docs/note.md` and
`docs/stato.md`.

**In progress:** none. `SEL-142` (cooperative fix) is resolved — see **Resolved** below; it spawned
`SEL-120`, `SEL-143` and `SEL-121`, all open.

| ID | Title | Area | Type | Priority | Status |
|----|-------|------|------|----------|--------|
| [SEL-143](SEL-143-cooperative-fabricated-from-unknown-reference.md) | Intent fabricates a hard `cooperative` verdict for an unknown reference game | chat / retrieval | Bug | High | Open |
| [SEL-101](SEL-101-langfuse-tracing.md) | Wire Langfuse tracing into the running stack | observability | Tech-debt | High | Open |
| [SEL-102](SEL-102-eval-model-digest.md) | Record the model weight digest in eval runs | eval | Tech-debt | Low | Open |
| [SEL-103](SEL-103-trace-token-counts.md) | Aggregate token counts into eval reports | observability | Feature | Medium | Open |
| [SEL-104](SEL-104-structured-output-retry.md) | Enforce structured LLM output with validated retry | ingestion/enricher | Feature | High | Open |
| [SEL-105](SEL-105-game-quality-score.md) | Compute a per-game quality score and gate on it | ingestion/enricher | Feature | Medium | Open |
| [SEL-106](SEL-106-webenricher-cache-extractions.md) | Cache Web enricher LLM extractions, not just fetches | ingestion/enricher | Refactor | Medium | Open |
| [SEL-108](SEL-108-unicode-normalization.md) | Normalize unicode in quote/label matching | ingestion/enricher | Tech-debt | Low | Open |
| [SEL-109](SEL-109-evaluate-qwen-gemma.md) | Evaluate Qwen2.5 / Gemma for Curator & Synth | ingestion/enricher | Research | Medium | Open |
| [SEL-110](SEL-110-litellm-transport.md) | Move LLM transport behind LiteLLM | enricher + chat | Refactor | Low | Open |
| [SEL-111](SEL-111-synth-eval-ragas.md) | Build a direct SynthEnricher eval (Ragas/DeepEval) | eval harness | Feature | Medium | Open |
| [SEL-112](SEL-112-consolidate-legacy-tests.md) | Consolidate legacy tests into the unified harness | tests | Tech-debt | Low | Open |
| [SEL-113](SEL-113-complete-agentic-chat.md) | Harden the agentic (tool-calling) chat engine | chat/agent | Feature | Medium | Open |
| [SEL-114](SEL-114-product-lineage-debug.md) | Product lineage journal + per-game debug endpoint | api/observability | Feature | High | Open |
| [SEL-115](SEL-115-tieredchat-checkpoint-txn.md) | Make TieredChat failover checkpoint-transactional | chat/tiered | Bug | Medium | Open |
| [SEL-116](SEL-116-user-memory-tier-routing.md) | User memory + Haiku→Sonnet tier routing | chat/state | Feature | Medium | Open |
| [SEL-117](SEL-117-ab-experiment-infra.md) | A/B experiment infrastructure | chat/state + api | Feature | Medium | Open |
| [SEL-118](SEL-118-concurrent-session-lock.md) | Define the concurrent-request contract for a session | chat/api | Tech-debt | Low | Open |
| [SEL-119](SEL-119-anthropic-prompt-caching.md) | Anthropic prompt caching for Synth on cloud | enricher + config | Feature | Medium | Open |
| [SEL-120](SEL-120-cooperative-inference-prompt-design.md) | Decide how the cooperative verdict is produced: dedicated inference vs. one enriched prompt | ingestion/enricher | Research | Medium | Open |
| [SEL-121](SEL-121-tickets-folder-vs-github-issues.md) | Decide whether to move the backlog from in-repo files to GitHub Issues | repo / process | Research | Low | Open |

## Resolved

Closed tickets live in [`resolved/`](resolved/).

| ID | Title | Area | Type | Resolved |
|----|-------|------|------|----------|
| [SEL-142](resolved/SEL-142-cooperative-not-understood.md) | Chat suggests the wrong kind of game for a "cooperative" request | chat / retrieval | Bug | 2026-06-23 |
| [SEL-107](resolved/SEL-107-multilingual-embedder.md) | Evaluate a multilingual embedder (bge-m3 / e5) — **adopted bge-m3** | rag/retrieval | Feature | 2026-07-03 |

## Conventions

- **ID**: `SEL-NNN`, monotonic. **Status**: Open / In progress / Done.
- Keep tickets short; link the source note (`docs/idee.md §X`) and the files they touch.
- A bug reported by a non-technical user stays in their words — the engineering analysis happens
  in the work, not in the ticket.
