# SEL-120 — Decide how the cooperative verdict is produced: dedicated inference vs. one enriched prompt

| | |
|---|---|
| **Type** | Research |
| **Area** | ingestion/enricher |
| **Priority** | Medium |
| **Status** | Open |

## Context

SEL-142 made `cooperative` a tri-state structured field (True / False / None). The value is decided
in `CuratorEnricher`: an explicit catalog co-op tag is the deterministic shortcut, otherwise the
mode is **inferred** from the description. That inference currently lives in a **separate LLM call**
(`_infer_cooperative` / `_coop_prompt`) kept apart from the verbatim extraction batch, because the
two have *opposite* anti-hallucination rules:

- the extraction prompt is grounded: "copy a VERBATIM quote or answer NESSUNO" — no inference;
- the cooperative prompt is the opposite: "reason about the MEANING, don't keyword-match".

Folding a free-judgment task into the grounded prompt risks weakening the verbatim discipline that
keeps the other labels clean; keeping them apart costs ~1 extra LLM call per game that has no co-op
tag (ingestion-time only). This ticket is to decide whether the separate call is justified.

## Options

1. **Keep the dedicated inference call (current).** Cleanest separation of the two prompt regimes;
   one extra call per tagless game.
2. **Fold the classification into the existing extraction prompt.** One call, fewer tokens, but it
   mixes grounded extraction with free inference in a single prompt — measure whether it degrades
   the verbatim labels' precision and/or the cooperative verdict's accuracy.
3. **Two equally-weighted prompts/passes.** Generalize to a clean split: one "grounded extraction"
   pass and one "semantic classification" pass as *peers* (not one nested inside the other), so
   future inferred attributes (genre tone, audience, competitive sub-type…) reuse the second pass
   instead of bloating the first.

## Proposed work

- Add the cooperative verdict to the existing Curator eval (slot-filling) so the options can be
  compared on the same fixtures: verdict accuracy **and** the verbatim labels' P/R as a guardrail
  against cross-contamination.
- Compare options 1–3 on accuracy, token cost, and latency; pick one. If option 3 wins, define the
  "classification pass" contract (which attributes it owns) so it doesn't become a dumping ground.

## Why it matters

The choice sets the pattern for every *inferred* (non-verbatim) attribute we add next. Getting the
prompt boundary right once avoids either silently eroding the extraction discipline or paying for a
separate call per attribute forever.

**Source:** SEL-142 work · **Touches:** `app/ingestion/enricher/curator.py`, `tests/eval/CuratorEnricher/`
