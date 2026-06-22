# SEL-112 — Consolidate legacy tests into the unified eval harness

| | |
|---|---|
| **Type** | Tech-debt |
| **Area** | tests |
| **Priority** | Low |
| **Status** | Open |

## Context

`tests/eval.py` and `tests/try_web.py` coexist with the newer `tests/eval/<Unit>/` structure,
doing similar things in different styles — confusing for newcomers.

## Proposed work

- Move `eval.py` logic into `tests/eval/Retrieval/` following the class/conftest convention.
- Decide `try_web.py`'s fate: a script (→ `scripts/`) or a test (→ migrate).

## Why it matters

One coherent test taxonomy; clearer project structure.

**Source:** docs/idee.md §K · **Touches:** `tests/eval.py`, `tests/try_web.py`, `tests/eval/`
