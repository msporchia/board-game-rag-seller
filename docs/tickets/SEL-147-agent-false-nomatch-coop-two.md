# SEL-147 — Agent arm: false honest-no-match on «cooperativo per due» (live session)

| | |
|---|---|
| **Type** | Bug |
| **Area** | chat/agent (search assembly) |
| **Priority** | High |
| **Reported** | 2026-07-03 |
| **Status** | Open |

## What happens

In the recorded live session ([showcase](../showcase/live-session.md), turn 3, real 501-game
index, `engine=agent` / qwen2.5:7b), the customer asks for *a cooperative game that plays well
in two*. The catalog has several (Magic Maze 1-8, Pandemic: La Caduta di Roma 1-5, Sherlock
1-8…), yet the agent's search returned **0 hits** and the turn fell to the honest no-match.
The anti-invention guarantee held (no game was made up — turn 4 then surfaces three genuinely
cooperative titles for five players), but the no-match was **false**: we do stock what was
asked.

## Suspects (not yet diagnosed)

- Malformed tool arguments from the model — the known qwen pattern the tool already coerces
  (e.g. `{"max": 180}`), but some shapes may still slip through into an over-restrictive
  filter (e.g. a duration carried from turn 2's «massimo un'ora» parsed into a nonsense bound).
- The turn-2 context (strategy, ≤60 min) folding into turn 3's filters in a way that
  over-constrains the coop search.

Diagnosis is currently blind: `traces` records the LLM calls but NOT the tool-call arguments —
exactly the SEL-114 lineage gap. First step: log `last_turn_searches` (query + filters +
n_hits per tool call) into the trace so a whiffed search is reconstructable post-hoc.

## Why it matters

The honest no-match is the seller's trust guarantee; a *false* no-match spends that trust on a
search bug. Same family as the June finding («honest framing can only be trusted once retrieval
surfaces the right candidate») — retrieval now works, the remaining risk moved into the agent's
search-assembly step.

**Source:** live demo session 2026-07-03 (`data/demo-chat-20260703.json`, gitignored) ·
**Related:** SEL-113, SEL-114, SEL-143 · **Touches:** `app/chat/agentic.py`,
`app/chat/tools/search_catalog.py`, tracing
