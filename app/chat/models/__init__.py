"""Chat schemas — the `/chat` contract (see docs/chat.md). One class per module:

- `request.ChatRequest`: what the frontend sends (one user turn; `session_id` present →
  stateful Phase 5 path, absent → stateless Phase 4).
- `reply.ChatReply`: the STRUCTURED output the LLM is constrained to produce. Each pitch is
  bound to its game `id` locally (`recommendation.ChatRecommendation`) so prose and cards
  cannot diverge: the customer-facing message is assembled in code from the pitches whose
  ids survive validation against the retrieved set (anti-hallucination: the model may not
  invent a game that was not retrieved — and an invented id loses its pitch too).
- `response.ChatResponse`: what the endpoint returns. The validated recommendation ids are
  hydrated back into the full `GameHit` objects the frontend needs to render cards.
- `analysis.TurnAnalysis` / `strategy.Strategy`: Phase 5 — the analyze node's structured
  output (the user-analysis dimensions + the escalation contract from docs/note.md) and the
  four selling strategies the deterministic router picks from.

Per-turn commercial steering is NOT a model here: `ChatRequest.custom_policy` is a list of
policy NAMES resolved into middleware by `app.chat.policies` (docs/idee.md §O).
"""
