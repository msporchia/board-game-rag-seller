# 0003 — Ship several interchangeable chat engines on one bench

**Status:** Accepted · recorded post-hoc 2026-06-19

## Context

"Who should drive the catalog search in a conversation?" has more than one defensible answer:
deterministic code, a code-piloted loop that lets the model reformulate the query, or a full agent
that drives a search tool itself. Each trades quality against token cost differently, and the right
answer is an **economic** call (how many tokens is one extra sale worth?) that depends on the
storefront — not a fact to settle once at design time.

It is not even one answer *per storefront*. Different customer segments plausibly sit at different
points on the quality/cost curve **at the same time**:

- a **retailer** or a known expert community (e.g. *la Tana del Goblin*) arrives with more
  background — worth spending the richer agent on, since the conversion is likelier and the
  customer can follow a deeper exchange;
- an **anonymous visitor** is a more uncertain purchase — here we may prefer to spend fewer tokens
  (the cheaper pipeline) until the intent firms up.

So the choice is per-conversation, not global — which is exactly why the engine is overridable
per request, not only by an env default. Committing to one engine up front would bake in a single
guess for every customer and throw away both the comparison and that per-segment flexibility.

## Decision

Define **one stable contract** — `reply(message, choices, k, session_id) -> ChatResponse` — and put
interchangeable engines behind it, selected by `CHAT_ENGINE` (and overridable per request for shadow
runs):

- **pipeline** — decomposed graph; every decision (route, filters, k) made in code, the weak 8B
  only writes the pitch.
- **piloted** — code-piloted loop; the model reformulates the query into *catalog language*, code
  fetches, a zero-result turn triggers one informed retry or an honest no-match.
- **agent** — the model drives a `search_catalog` tool itself; the reply is still assembled in code
  over what the tool returned (same grounding as [ADR-0002](0002-grounding-enforced-in-code.md)).

`TieredChat` (`app/chat/tiered.py`) wraps a primary engine that *may* fail around a fallback that
must not, so any engine degrades down the ladder to the deterministic reply. All engines share one
checkpointer, so a session is portable across whichever arm serves a turn.

## Alternatives considered

- **Pick one engine (the pipeline) and ship it.** Cheapest to build, but it answers the design
  question by assertion. We would never learn that the agent converts hard cases the deterministic
  router cannot, nor what that conversion costs per chat.
- **A/B at the product layer only.** Possible, but without one internal contract each engine would
  drift its own response shape, and the eval could not replay the *same* fixtures across arms.

## Consequences

- The engines are measured **head to head on the same `ChatConversation` fixtures**: pipeline
  **0.70**, piloted **0.80 at −18% tokens**, agent **0.867** — read as a **quality/cost curve**, not
  a leaderboard. Which arm a storefront runs becomes a deliberate, evidence-backed choice.
- **Honest caveat:** the agent is **stochastic** — the same 15 cases scored 0.60 / 0.80 / 0.87
  across three runs. The numbers are a sample, not a verdict, and are session-stamped so a stale one
  reads as stale.
- **A structure that holds several arms is cheap to keep.** Because they share one contract and one
  checkpointer, hosting more than one engine carries little structural cost — and it lets the same
  storefront route different customers (retailer, expert community, anonymous visitor) to different
  arms at once. Branches that stop earning their keep can simply be **pruned**: deleting an engine
  is removing one implementation behind the contract, not unpicking it from the rest of the system.
- **Cost:** every engine must honor the one contract and the shared checkpointer — more discipline,
  and a wider surface to test (one eval suite per node, plus the whole-conversation suite).
- The `TieredChat` seam exists and is exercised, but its **circuit breaker** (stop paying for a
  primary that keeps failing) is still designed-only — tracked in [`docs/idee.md` §Q](../idee.md).
