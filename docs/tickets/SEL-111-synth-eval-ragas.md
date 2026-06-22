# SEL-111 — Build a direct SynthEnricher eval (Ragas / DeepEval)

| | |
|---|---|
| **Type** | Feature / Eval |
| **Area** | eval harness |
| **Priority** | Medium |
| **Status** | Open |

## Context

Synth's job is synthesis (faithfulness, completeness, relevance), not slot-filling — yet today
it's measured only indirectly (downstream retrieval recall). No direct quality gate exists.

## Proposed work

- Add a `tests/eval/SynthEnricher/` suite using Ragas (`faithfulness ≥ 0.9`, completeness per
  canonical label) or DeepEval, with a different/stronger model as judge to avoid self-bias.

## Why it matters

Gives Synth a graduation gate to production and catches synthesis regressions directly.

**Source:** docs/idee.md §F + docs/stato.md · **Touches:** `app/ingestion/enricher/synth.py`, new `tests/eval/SynthEnricher/`
