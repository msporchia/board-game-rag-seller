# SEL-146 — Revisit the cooperative verdict: the SEL-145 policy is a stopgap

| | |
|---|---|
| **Type** | Research / Feature |
| **Area** | ingestion/enricher + rag/retrieval |
| **Priority** | High |
| **Reported** | 2026-07-03 |
| **Status** | Open |

## Context

SEL-145 shipped a deliberately conservative policy (`cooperative` True only from the curated
catalog signal; False only from the evidence-gated inference; everything else None). It was
accepted **as a stopgap**: it never lies — the property the hard filter needs — and it
unblocked testing the prompts and the pipeline on honest data. The price is recall: untagged
co-op games sit at None and never enter the coop-filtered set. Classifying a board game's play
mode is not intrinsically hard; it is hard *for an 8B reading only retail marketing*. This
ticket owns getting the recall back without giving up the zero-wrong-verdict rule.

## Measured leads (collected 2026-07-03, in ROI order)

1. **Independent oracle re-verification first.** The suite oracle's cooperative labels are
   bootstrapped from the same catalog tags as the True shortcut — circular on the True axis, so
   it cannot credit the classifier for co-op games the tags missed (Dungeon Saga is the live
   example: the description states team-vs-evil play, the label set has no `Cooperativo`).
   Re-verify the ~20 games involved in the v1-v3 differences against an external ground truth
   (BGG); print-and-adjudicate is already the habit — make the verified labels the new oracle.
2. **Stronger model on the same gate.** The v3 prompt + verbatim-proof validation are in place;
   the strict e2e gate (zero wrong verdicts, either direction) is the acceptance test. Run the
   same classification with a frontier model (the ChatConversation simulation harness pattern,
   or the API once SEL-110 lands) — if it clears the verified oracle, inferred True earns the
   seat back. Cross-ref SEL-109.
3. **The name is curated signal too.** Retail names in this catalog often declare the mode
   («… - Gioco Cooperativo per Famiglie …»). Measured: +0 on the suite (tags already cover it),
   **+2 recall on the live 501** (Zombicide, Fallout: New California) with 0 false positives —
   cheap, deterministic, worth taking with the rest of the revisit.
4. **Reviews as the truth source.** The proven ceiling of description-based inference is a
   *lying source* (Warhammer HoBR marketed as «lavoro di squadra»). The WebEnricher already
   fetches trusted review domains for gap-filling: the play mode is exactly the kind of fact
   reviews state plainly and marketing distorts.

**Source:** SEL-145 resolution · **Related:** SEL-145 (resolved), SEL-120, SEL-143, SEL-109,
SEL-110 · **Touches:** `app/ingestion/enricher/curator.py`, `app/ingestion/enricher/prompts.py`,
`tests/fixtures/suites/core/labels.json`
