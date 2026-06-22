# SEL-108 — Normalize unicode in quote/label matching

| | |
|---|---|
| **Type** | Tech-debt |
| **Area** | ingestion/enricher |
| **Priority** | Low |
| **Status** | Open |

## Context

`Curator._norm` and `Web._normalize` do only `lower().split()`. Italian accents (NFC vs NFD) and
typographic apostrophes (`'`) cause spurious false negatives — a label is lost for string
reasons, not content.

## Proposed work

- Apply `unicodedata.normalize("NFKC", s)` and fold typographic apostrophes to ASCII `'` before
  comparison.

## Why it matters

Removes a small but real source of missed labels; detectable by re-scanning `runs/last.json`.

**Source:** docs/idee.md §I · **Touches:** `app/ingestion/enricher/web.py`, `app/ingestion/enricher/curator.py`
