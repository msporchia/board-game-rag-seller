# SEL-143 — Intent fabricates a hard `cooperative` verdict for an unknown reference game

| | |
|---|---|
| **Type** | Bug |
| **Area** | chat / retrieval (intent) |
| **Priority** | High |
| **Status** | Open |

## Context

Follow-up to the SEL-142 fix. The `cooperative` shape is now fully wired end-to-end —
`SearchIntent.cooperative` → `to_filters_spec` → `CooperativeFilter`, with the `INTENT` prompt
(`prompts.py` §PilotedChat) and the `search_catalog` tool description both instructing the field.
The mechanism works in most cases: explicit "cooperativo" → `True`, a paraphrase like "giochiamo
tutti insieme contro il gioco" → `True` (no keyword needed), a known reference like "come Pandemic"
→ `True`, "competitivo" → `False`.

It fails on the exact scenario SEL-142 came from: a customer naming a reference game *without*
the modal word.

## What happens

Prompt (qwen2.5:7b intent step), no quick-reply filters active:

> voglio un gioco come le cronache di avel, cosa mi consigli?

The model emits `cooperative = False` (and `players = 2`, neither stated). *Le Cronache di Avel* is
a cooperative game we don't carry; the model has no real knowledge of it, so it guesses from the
name (imagines a medieval euro-strategy title) and *fabricates* a competitive verdict.

Two compounding failures:

1. **It violates the prompt's own instruction.** The field doc says *"Lascia null se non esprime
   una preferenza — non dedurla dal tono."* The customer stated no mode, so the correct value is
   `null` (abstain). The model deduces `False` anyway, from a hallucinated mental model of the
   named game.
2. **`False` is worse than `null`.** `CooperativeFilter {"val": False}` is a hard filter that keeps
   only games flagged competitive and **excludes every cooperative game** (co-op titles are `True`,
   unknowns are `None` — both filtered out). So the new shape doesn't merely miss the co-op intent
   here, it actively steers the catalog toward the *opposite* of what the customer wants.

The same hallucinate-then-launder pattern shows up in the free-text `query`: the reformulation for
this turn was "gioco di strategia e gestione risorse … tema storico medievale" — the inverse of
Avel's actual cooperative-fantasy-family profile.

## Evidence (intent step, temperature 0)

| Customer message | `cooperative` | Correct? |
|---|---|---|
| "gioco **cooperativo** come le cronache di avel" | `True` | ✓ explicit word |
| "gioco **come le cronache di avel**" | **`False`** | ✗ should be `null` |
| "gioco **come pandemic**" | `True` | ✓ model knows Pandemic |
| "**giochiamo tutti insieme contro il gioco**" | `True` | ✓ semantic, no keyword |
| "gioco **competitivo** per due" | `False` | ✓ explicit |

So the gap is narrow and specific: the model abstains correctly when it has *no* signal, but when
it (wrongly) believes it knows an obscure named game, it treats that belief as a stated preference
and emits a confident hard filter.

## Direction to explore (not decided)

- Constrain `cooperative` to fire only from **explicit modal language** or a reference the model is
  confident it knows — never from a guessed one; default to `null` on doubt. The curator already
  follows this discipline (`_infer_cooperative` returns `None` on "incerto"); the intent step
  should match it.
- Consider whether a named reference game should be grounded against the catalog/a source before
  its mechanics are trusted, rather than recalled from the model's parametric memory (shared root
  cause with the broader "a game like X" weakness).
- Re-check on a stronger model (SEL-109) — this may partly be an 8B recall/abstention limitation.

## Why it matters

This is the same customer-facing harm as SEL-142 (cooperative request → competitive suggestions),
but now produced *by* the fix, as a confident filter rather than a soft retrieval miss — which makes
it harder to spot and more damaging when it fires.

**Source:** session diagnosis of SEL-142 · **Touches:** `app/chat/prompts.py` (`INTENT`,
`SEARCH_CATALOG`), `app/chat/models/intent.py`, `app/rag/filters/bool/cooperative_filter.py`
