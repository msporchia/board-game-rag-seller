# SEL-144 — Under bge-m3 the Synth turned net-negative: recalibrate it as the representation normalizer

| | |
|---|---|
| **Type** | Bug / Recalibration |
| **Area** | ingestion/enricher (synth) + rag/retrieval |
| **Priority** | High |
| **Reported** | 2026-07-03 |
| **Status** | Resolved (2026-07-03) — synth v2 shipped, criteria met (one noted miss) |

## Context — what changed

SEL-107 swapped the embedder to `bge-m3` and moved the whole operating point: the embedder is
no longer the weakest compressor in the chain. The Synth's v1 tuning (compress the description
to ≤700 chars) was an adaptation to `nomic`'s dilution problem — under bge that compression
destroys signal a strong embedder would have used. Full evidence: `docs/experiments.md` rows 5-8.

## What we measured (suite `core`, K=5, bge-m3)

| variant | embed chars (typ.) | R@5 | P@5 | err |
|---|---|---|---|---|
| `rule` (cap 1800) | ~2.4k | **0.43** | **0.67** | 0.20 |
| `rule-uncapped` (full text) | ~3.5k | 0.39 | 0.60 | 0.19 |
| `synth` v1 (replace, ≤700) | ~1.3k | 0.40 | 0.60 | 0.21 |
| `synth-append` (experiment) | ~4.2k | 0.41 | 0.65 | 0.18 |

Findings the decision rests on:

1. **Semantic saturation exists under bge too** — returns invert around ~2-2.5k chars
   (`rule-uncapped` < `rule`). "Give the embedder everything" is falsified (row 7).
2. **Synth v1 loses ~1-2 aggregate hits but buys the cooperative axis clean**
   (0.83 / P 1.00 / err 0.00 — the only clean query ever recorded, both synth arms).
3. **Positional truncation cuts gold**: the 1800 cap chops concept-bearing sentences
   («la collaborazione è fondamentale» sits at char ~1850 of Massive Darkness). Part of the
   synth's coop win is that it reads the FULL description and smuggles those concepts back in.
4. **Mechanic axes (worker placement) die under prose mass in every variant** (0.27 terse →
   0.09-0.18 long). Prose cannot carry that axis: it belongs to structured signal
   (tags → filters/boost; cooperative flag → SEL-142, backfill pending).
5. **Honest negative**: global text homogeneity does NOT indict the 8B — mean pairwise cosine
   of synth-v1 texts (0.583) is slightly *lower* than raw marketing (0.595). If flattening
   hurts, it is within-axis, not global; to be re-verified per-axis, not assumed.

## Decision (reasoned with the four cells on the table)

The Synth is the **representation normalizer**: raw descriptions are untrusted input; every
game exits the synth in the same format at the same density, containing only verified facts
and searchable concepts. We pilot the embedder — we don't implicitly trust sources.
Append-mode was considered (best err, 0.18) and **rejected on concept**: untrusted text would
keep reaching the embedder, and length normalization (no game advantaged by verbose marketing)
would be lost.

Recalibration (v2):
- **Budget 700 → 1600 chars** — the measured sweet spot is ~1.5-2k; v1 normalized *below* the
  optimum.
- **Prompt v2**: coverage checklist for searchable concepts (mechanics by their precise names,
  what you actually do in a turn, setting/theme with proper nouns, audience/occasion, tone);
  explicit ban on could-be-any-game phrasing; keep the distinctive words of the material.
- **Unchanged**: replace mode, never restate structured numbers (Compose owns them), never
  invent (facts only from the material), Italian prose.
- The compose 1800 cap stays as a pure failsafe (the synth output is the description on the
  production path; raw text no longer reaches the embedder there).

## Success criteria (declared before the run)

- Suite aggregate ≥ `rule`/bge (R@5 ≥ 0.43) — the normalizer must not tax retrieval.
- Cooperative query stays clean (err 0.00).
- e2e stripped-source gate (`tests/e2e/enrichment`) stays green — recovery must not regress.
- If aggregate lands < 0.43, the ticket stays open with the numbers and the next lever
  (stronger synth model, SEL-109 / strong-model simulation) takes over.

## Resolution (2026-07-03) — synth v2 shipped and measured (ledger row 9)

| criterion | outcome |
|---|---|
| aggregate ≥ `rule`/bge (R@5 ≥ 0.43) | ✅ **0.43** (P@5 0.65, err 0.19 — best err of any replace-mode arm; v1 was 0.40/0.60/0.21) |
| cooperative query stays clean | ⚠️ met in substance, missed on the letter: 0.83 / P@5 **1.00** / 1st-rel #1, but err **0.02** (one inversion deep below the top-5; v1 was 0.00) |
| e2e stripped-source gate green | ✅ no regression; TM recovery 2.33→1.33 intact; embed lengths grew to the new budget (947→1980 etc.) |

The normalizer now costs **zero aggregate recall** versus trusting the raw capped text, while
buying the cooperative axis (0.83 vs 0.67) and storytelling (0.40→0.60). Chronic residuals are
explicitly *not* this ticket's scope and are delegated: worker-placement (0.18) and
aste/offerte (0.14) belong to structured signal (SEL-142 backfill + filters) and/or a stronger
synth model (SEL-109). Side note recorded for honesty: the global text-homogeneity metric
(mean pairwise cosine) proved non-diagnostic — v2 0.594 ≈ raw marketing 0.595, v1 0.583.

**Source:** docs/experiments.md rows 5-9 · **Related:** SEL-107 (resolved), SEL-142, SEL-109,
SEL-111 · **Touches:** `app/ingestion/enricher/synth.py`, `app/ingestion/enricher/prompts.py`
