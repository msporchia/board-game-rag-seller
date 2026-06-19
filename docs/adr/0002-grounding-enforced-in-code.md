# 0002 — Enforce anti-hallucination in code; assemble the reply in code

**Status:** Accepted · recorded post-hoc 2026-06-19

## Context

The seller must only ever recommend **real, in-stock games** — never a plausible-sounding title
that is not on the shelf. An LLM writing free-form sales prose will, sooner or later, name a game
that was not retrieved, or write a pitch whose text and whose cards disagree. The first measured
failure was exactly that: prose and cards naming different games.

The question is *where* the "only real games" rule lives — in the prompt (the model is asked to
obey) or in the code (the model cannot disobey).

## Decision

Put the rule in the code. The LLM never emits free prose about games. It returns **structured
output** — an intro plus per-game `{id, pitch}` pairs (`ChatReply`) — referencing games only by the
`id` we handed it. Then, in `ChatAdvisor.pitch` (`app/chat/advisor.py`):

1. **Validate every id against the retrieved set.** An id that was not retrieved is dropped —
   *together with its pitch*. Each id is kept at most once.
2. **Assemble the customer message in code** from the surviving intro + pitches. The prose is
   therefore built from the cards, so it can only ever describe games that are on the cards.

Prose↔cards incoherence is not patched after the fact; it is **structurally impossible**.

## Alternatives considered

- **Trust the prompt** ("recommend only from this list"). This is what the model already gets — and
  small local models still break it. A rule that matters cannot live only where it can be ignored.
- **Post-hoc string/regex check** on free-form prose. Brittle (titles vary, are inflected, get
  abbreviated) and it can detect a bad mention but not cleanly *remove* it from flowing text.
- **Let a structured-output failure 500.** Rejected: a transport failure on a weak model is normal,
  not exceptional, and must never cost the customer a turn.

## Consequences

- The anti-hallucination guarantee holds regardless of model quality — it is the same on the weak
  8B and on a strong model. The grounding rules in the prompt (`GROUNDING_RULES`) become a *hint*,
  not the enforcement.
- **Deterministic fallback** is mandatory and built: if structured output fails, or no picked id
  survives validation, the turn degrades to an honest scripted reply over the top hits
  (`_fallback`). No 500, no invented recommendation.
- **Cost:** we trade away the local model's free-flowing copy for a rigid `{id, pitch}` shape the
  weak 8B sometimes fails to produce — which is *why* the fallback exists, and part of why pitch
  quality on the small model is the open bottleneck (README, "Still being finalized").
- The same `pitch()` path is reused by both the stateless `reply()` and the stateful graph, so the
  guarantee is enforced in exactly one place rather than re-implemented per engine.
