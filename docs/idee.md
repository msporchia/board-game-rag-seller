# Ideas & levers — now tracked as tickets

This file used to be the operational brain-dump of every lever worth pulling. It grew
unmanageable, so the actionable items have been **formalized into the ticket backlog**
(`docs/tickets/`, indexed in `docs/tickets/README.md`). Each former section maps to a ticket
below — nothing is lost, it just lives somewhere with an ID, a status and a single owner.

What stays here: the **shipped record** (work that is no longer an idea), the **design red
lines**, and the few **raw ideas not yet scoped** into a ticket.

---

## Formalized into the backlog

| Former § | Lever | Ticket |
|----------|-------|--------|
| A | Structured output with schema enforcement | [SEL-104](tickets/SEL-104-structured-output-retry.md) |
| B | Tracing / observability (Langfuse) | [SEL-101](tickets/SEL-101-langfuse-tracing.md) |
| C | Multilingual embedder (bge-m3 / e5) | [SEL-107](tickets/SEL-107-multilingual-embedder.md) |
| D | Stronger enricher model (Qwen2.5 / Gemma) | [SEL-109](tickets/SEL-109-evaluate-qwen-gemma.md) |
| E | LiteLLM provider-agnostic transport | [SEL-110](tickets/SEL-110-litellm-transport.md) |
| F | Direct SynthEnricher eval (Ragas / DeepEval) | [SEL-111](tickets/SEL-111-synth-eval-ragas.md) |
| G | Per-game quality score | [SEL-105](tickets/SEL-105-game-quality-score.md) |
| H | Model weight digest in eval runs | [SEL-102](tickets/SEL-102-eval-model-digest.md) |
| I | Unicode normalization in quote matching | [SEL-108](tickets/SEL-108-unicode-normalization.md) |
| J | Full WebEnricher idempotency | [SEL-106](tickets/SEL-106-webenricher-cache-extractions.md) |
| K | Consolidate legacy tests | [SEL-112](tickets/SEL-112-consolidate-legacy-tests.md) |
| L | User memory + Haiku→Sonnet tier routing | [SEL-116](tickets/SEL-116-user-memory-tier-routing.md) |
| M | Product lineage + per-game debug endpoint | [SEL-114](tickets/SEL-114-product-lineage-debug.md) |
| O (residual) | A/B arm assignment + conversion loop | [SEL-117](tickets/SEL-117-ab-experiment-infra.md) |
| P | Concurrent-request contract per session | [SEL-118](tickets/SEL-118-concurrent-session-lock.md) |
| Q (residual) | Harden the agentic chat engine | [SEL-113](tickets/SEL-113-complete-agentic-chat.md) |
| Q (residual) | Token counts → cost per arm | [SEL-103](tickets/SEL-103-trace-token-counts.md) |
| Q (residual) | Transactional failover checkpoint | [SEL-115](tickets/SEL-115-tieredchat-checkpoint-txn.md) |
| — | Cooperative mechanic as a retrieval signal (from `note.md`) | [SEL-142](tickets/resolved/SEL-142-cooperative-not-understood.md) (resolved) |

Anthropic prompt caching for Synth (from `note.md`) → [SEL-119](tickets/SEL-119-anthropic-prompt-caching.md).

---

## Shipped (no longer ideas — kept here as the short record; detail in `stato.md`)

- **Policy middleware seam** (was §O, built 2026-06-17). The turn carries `custom_policy:
  [name, ...]`; `PolicySet` resolves names to one-class-per-file `Policy` objects (hardcoded
  `REGISTRY`, unknown names logged-and-skipped) composed as middleware around `retrieve`/
  `generate`. Starter policies: `christmas_sale`, `promote_cooperative`, `assume_advanced`,
  `force_quick_match`. Active names logged per node; each policy unit-tested in isolation.
  Remaining (experiment arms + conversion loop) → SEL-117.

- **Three chat engines behind one contract** (was §Q). `pipeline` (weak local model, every
  decision in code), `piloted` (model expresses a structured recommendation intent, code
  fetches and loops on zero results), `agent` (strong model drives a `search_catalog` tool).
  `TieredChat` is the seam: a primary that may fail over a fallback that must not; grounding,
  the ChatResponse contract and the honest no-match stay in code at the boundary for all three.
  Measured deltas worth remembering:
  - piloted vs pipeline (llama3.1, 2026-06-12): case pass **0.700 → 0.800**, convergence
    5/8 → 6/8, tokens **−18%** for +4 LLM calls. Recovered the text-borne-refinement and the
    constraint-reversal failures; surfaced one regression (the 8B inventing a duration filter
    on a title lookup).
  - agent (2026-06-18): `qwen2.5:7b` drives the tool end-to-end (~8–10s/turn, fits the 8GB box);
    `llama3.1:8b` cannot, `qwen3:14b` thrashes. ChatConversation case pass **0.867**.
  Remaining (scored eval + session history + circuit breaker → SEL-113; engine-tagged traces +
  token cost → SEL-103; transactional checkpoint on failover → SEL-115).

---

## Not yet scoped (raw idea — do NOT build yet)

- **Adaptive source count in the WebEnricher** (was §N). Today `max_sources` is a fixed cap (3).
  Make it adaptive between a min floor and a max ceiling, driven by quality signals (residual
  `missing_info`, judge pass-rate, extraction yield per page) rather than a fixed count: stop
  early on an easy game, widen the pool on a hard one. No new infrastructure — a smarter loop
  guard in `WebEnricher`, reusing the same signals as the quality score (SEL-105). Promote to a
  ticket only once SEL-105 lands (it shares the signals). Measure: per-game source distribution
  (expected bimodal), LLM calls saved vs the fixed cap, with no recall loss on poor sheets.

---

## Red lines I would NOT change

Current choices that, if revisited, should be revisited by **measuring**, not "because I read a
blog post":

- **Linear Enricher pipeline** (not LangGraph) for ingest — the workload is linear batch with
  zero shared state between steps of the same game.
- **Two-store: regenerable Qdrant + durable SQLite** — enterprise IR textbook; no "everything in
  Qdrant".
- **Immutable `original` + `enriched` working copy** — the invariant that lets you reconstruct
  any step. Don't sacrifice it for "simplicity".
- **Citation-grounded extraction with verbatim validation** — the anti-hallucination pattern.
  Don't replace it with "trust the model" even as models improve.
- **Unit (FakeLLM, offline) vs eval (real LLM, `llm` marker)** — correct separation; don't merge
  them "for CI convenience".
- **Slot-filling F-β + record/replay for the LLM steps** — the right measure of the task.

---

## When to re-read this file

- Before deciding the **next step** after a session (usually: measure → pick the next ticket).
- When deciding to go to cloud → SEL-101 + SEL-110 together.
- Before writing the SynthEnricher eval → SEL-111 first, not after.
