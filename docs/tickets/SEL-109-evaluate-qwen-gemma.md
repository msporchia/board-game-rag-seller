# SEL-109 — Evaluate Qwen2.5 / Gemma for Curator & Synth

| | |
|---|---|
| **Type** | Research / Eval |
| **Area** | ingestion/enricher |
| **Priority** | Medium |
| **Status** | Open |

## Context

Curator passes 3/10 on the core suite; most residual misses are genre mis-recognition and
gap-detection edge cases. A better instruction-follower is an orthogonal lever to prompt tuning.

## Proposed work

- Run `qwen2.5:7b-instruct` and `gemma:9b` against the Curator and Synth evals.
- Compare F-β / faithfulness vs llama3.1; keep the winner per step.

## Why it matters

These models follow instructions and emit cleaner Italian JSON; may close the Curator gap without
more prompt engineering.

**Source:** docs/idee.md §D + docs/stato.md · **Touches:** `app/config.py`, `tests/eval/CuratorEnricher/`
