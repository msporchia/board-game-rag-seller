# SEL-102 — Record the model weight digest in eval runs

| | |
|---|---|
| **Type** | Tech-debt |
| **Area** | eval / quality |
| **Priority** | Low |
| **Status** | Open |

## Context

Eval runs (`runs/*.json`) store the model name (`"llama3.1"`) but not the underlying weight
digest. When Ollama re-pins a model, run-to-run diffs become misleading without anyone noticing.

## Proposed work

- Capture the `FROM <sha>` digest from `ollama show --modelfile` at run time.
- Add it to the run record schema and surface it in the report headline.

## Why it matters

Makes longitudinal eval comparisons trustworthy; prevents a silent model swap from masquerading
as a quality regression.

**Source:** docs/idee.md §H · **Touches:** `tests/eval/report/eval_report.py`, recorders under `tests/eval/*/`
