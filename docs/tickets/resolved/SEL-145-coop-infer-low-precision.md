# SEL-145 — COOP_INFER classifies competitive games as cooperative: the SEL-142 bug returns through the fix itself

| | |
|---|---|
| **Type** | Bug |
| **Area** | ingestion/enricher (curator, COOP_INFER) + rag/retrieval |
| **Priority** | High |
| **Reported** | 2026-07-03 |
| **Status** | Resolved (2026-07-03) — **as an accepted stopgap**: revisit tracked in SEL-146 |

## What happens

The first-ever live backfill of the `cooperative` flag (501 products, 2026-07-03) produced
**237 True** — 123 from the deterministic catalog-tag shortcut (reliable) and **114 from the
`COOP_INFER` LLM inference**. A spot-check of the inferred set found blatantly competitive
games classified cooperative: *Ticket to Ride* (two editions), *Talisman*, *Dixit*,
*Kanagawa*, *Orbis*, *Warhammer 40,000: Heroes of Black Reach*.

Pattern: llama3.1 reads family/social marketing («da giocare tutti insieme», «divertimento con
gli amici») as *cooperative play*, instead of the strict definition (players win or lose
**together against the game system**).

## Why it matters

A hard `CooperativeFilter` with heavy false positives **re-creates the original SEL-142
complaint through the fixed pipe**: a customer asking for a cooperative game now gets
competitive titles *with the filter on*. Worse than the original soft miss (SEL-143's point):
the wrong verdict is now confident, structured and invisible.

Also contaminated: the frozen eval corpus regenerated today (19 True / 27 False / 4 None on
50 games) uses the same inference — the coop-case oracles in ChatConversation sit on top of it.

## Measurement (in progress → results below)

The suite's hand-curated `labels.json` is an oracle for the 50-game corpus: run
`_infer_cooperative` on every raw description, score precision/recall of the «cooperativo»
verdict. Then iterate the `COOP_INFER` prompt against that number (same direct-probe loop the
Curator used for v1→v4).

## Proposed fix

1. Measure v1 (baseline to beat).
2. `COOP_INFER` v2: strict definition in the prompt («cooperativo SOLO se i giocatori vincono
   o perdono INSIEME contro il gioco; giocare in famiglia/in gruppo NON è cooperativo»), demand
   textual evidence, push doubt to «incerto» much harder.
3. Re-measure vs oracle; ship only if precision(True) is high (the flag feeds a HARD filter —
   precision beats recall here; a None costs nothing, a wrong True poisons retrieval).
4. Re-run the backfill for inference-derived verdicts (tag-True untouched) + re-patch the
   frozen corpus's `cooperative` fields.

## Resolution (2026-07-03)

Acceptance rule set by the product owner: **a false verdict in either direction is
unacceptable — better no filter contribution than a wrong one**; the model must lean hard on
abstaining. Measured against the hand-curated suite oracle (50 games, 6 cooperative):

| COOP_INFER config | «cooperativo» verdicts | wrong True | wrong False | abstentions |
|---|---|---|---|---|
| v1 | 18 | **12** (prec 0.33) | 0 / 28 | 4 |
| v2 — strict definitions + named traps | 12 | **6** (prec 0.50) | 0 / 32 | 6 |
| v3 — abstention-first + **verbatim proof validated in code** | 6 | **2** (prec 0.67) | 0 / 2 | 42 |

v3 adds the house discipline: a verdict counts only with a quote the code re-finds verbatim in
the description (`_infer_cooperative` + `_quote_in_text`). Adjudication of its two residual
false Trues is itself informative:
- *Dungeon Saga* — the description literally states team-vs-evil co-op play; the bootstrapped
  oracle label is arguably incomplete (ambiguous 1-vs-many game). Oracle gap, not model gap.
- *Warhammer 40,000: Heroes of Black Reach* — a head-to-head wargame whose **marketing itself
  lies** («lavoro di squadra… unendo le forze»). The quote is verbatim and the verdict is still
  wrong: **no validation can save an inference from a source that says false things.** This is
  the measured ceiling of description-based inference on retail copy.

**Shipped policy (strict gate applied per direction):**
- **True — catalog signal only** (`_catalog_says_cooperative`). The inference's True is capped
  to None in `_cooperative_verdict` even when proven: 2 FP at v3 fail the zero-error rule.
- **False — inference allowed**: zero wrong False across all three configs (62 verdicts).
- **None — everything else** (the default the model is pushed toward).
- v3 prompt + verbatim-proof validation ship as the classifier; the e2e test is now the strict
  symmetric gate (a wrong direction fails, abstention always passes) and SEL-109 owns the
  ambition of earning True back with a stronger model.

Applied to data: live store + Qdrant payloads and the frozen eval corpus realigned to the
shipped policy (tag-True kept; all other verdicts recomputed with v3, True capped). Live smoke:
the family-coop query with `cooperative=true` returns 5/5 genuinely cooperative games.

**Framing, on purpose: this is a stopgap, not the destination.** It was accepted because it
never lies (the property the hard filter needs) and it unblocked testing the prompts and the
rest of the pipeline on honest data — at the price of recall on untagged co-op games. The
revisit is a first-class ticket, [SEL-146](../SEL-146-cooperative-verdict-revisit.md), with the
measured leads already collected (independent oracle re-verification, stronger-model
classification, the name signal, reviews as a truth source).

**Source:** live backfill spot-check · **Related:** SEL-142 (resolved), SEL-143, SEL-120,
SEL-109 · **Touches:** `app/ingestion/enricher/prompts.py` (COOP_INFER),
`app/ingestion/enricher/curator.py`, backfill ops
