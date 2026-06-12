# 💬 Chat — a conversation, before → after (🚧 placeholder)

> **Status: structure only.** The conversational layer runs end-to-end but isn't finalized;
> this walkthrough will be filled with a **real recorded session** once it is. What follows is
> the contract for what will be shown — same discipline as the
> [pipeline walkthroughs](README.md): real inputs, measured behaviour, failures included.

The pipeline walkthroughs show what enrichment does to *one game*. This one will show what the
conversational layer does to *one customer*: the same opening request handled by the stateless
Phase 4 endpoint (one shot, no memory) versus the stateful Phase 5 conversation (memory,
strategy, clicks that become filters) — before → after, on the same catalog.

## The five beats (mirroring the pipeline walkthroughs)

1. **① The opening turn** — the raw user message; the `TurnAnalysis` read of the customer
   (enthusiasm, decisiveness, expertise) and the strategy the deterministic router picks
   (GUIDED / EXPLANATORY / DISCOVERY / QUICK MATCH).
2. **② Retrieval** — the query and filters assembled from the turn, and the real hits the
   hybrid retriever returns.
3. **③ The grounded pitch** — the structured `{intro, recommendations, quick_replies}` reply,
   which ids survived grounding validation, and the customer message assembled in code.
4. **④ The follow-up turn** — session memory in action: a quick-reply click parsed into real
   `SearchFilters`, the strategy adapting to the new read of the customer.
5. **⑤ Enforced vs generated** — which parts of the transcript are *guaranteed by code*
   (anti-hallucination grounding, coherence by construction, deterministic fallback) and which
   are *produced by the LLM* (and therefore measured, not trusted).

## Planned scenarios

| Scenario | What it must show |
|----------|-------------------|
| **Guided discovery** | a vague request converging in a few clicks — quick replies → filters → narrower table |
| **Quick match** | a decisive customer getting ≥ 3 concrete proposals in one turn |
| **Honest no-match** | empty retrieval short-circuiting to a truthful "niente in catalogo" — no LLM, no invention |

Each scenario will be shown twice: the **rendered transcript** (what the customer sees) and the
**trace** (what each graph node did), with the per-step eval rates that back it —
[TurnAnalyzer](../../tests/eval/TurnAnalyzer), [ChatPitch](../../tests/eval/ChatPitch),
[ChatRetrieve](../../tests/eval/ChatRetrieve),
[ChatConversation](../../tests/eval/ChatConversation) (whole sessions, end-to-end).

→ Design and first findings: [`docs/chat.md`](../chat.md) · back to the
[other walkthroughs](README.md).
