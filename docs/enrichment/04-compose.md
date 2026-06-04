# Step 4 — Compose

**Status:** ✅ implemented (rule-based) · **Code:** `app/ingestion/enricher/compose.py`
(`RuleComposeEnricher`)

## Why this step exists

The vector store doesn't embed a record with fields — it embeds **one string**. Everything
upstream curated the *data* (certain fields, extractions, web facts, a synthesized description);
Compose is the final assembly that turns that curated record into the single `embed_text` that
actually gets embedded.

It is the **last control point over what the embedder sees, and in what order**. That matters:
the embedding is a "semantic centroid" of the text (see `docs/valutazione.md`), so *what we
include* and *how we phrase it* directly shape which queries the game will match. Compose is
where representation engineering lands in concrete output.

## What it does

`RuleComposeEnricher` is **deterministic** (no LLM): it turns the `enriched` fields into plain
natural-language sentences and concatenates them, in a fixed order, into `embed_text`:

1. **name**
2. **players** — with notes ("giocabile in solitario", "ottimo in due", "per gruppi numerosi")
3. **duration** — with a qualitative label ("partita breve e veloce", "durata media…")
4. **complexity** — with a beginner/expert hint
5. **tags** — "Meccaniche e temi: …"
6. **meta** — categoria, autori, editore, anno, expansion flag
7. **description** — capped at 1800 chars

The result is the joined non-empty blocks. (If `embed_text` somehow ends up empty, the
serializer falls back to the game's name.) Because it's deterministic, it's also the **baseline
to beat** and the stable final assembler the LLM steps feed into.

## How we expect it to behave

- **Deterministic and reproducible.** Same input → same `embed_text`, always. No model, no
  variance.
- **Order is part of the strategy.** It's a single step on purpose — word order shapes the
  centroid, so it lives in one place we control.
- **Surface the canonical facts as explicit phrases.** Players/duration/complexity/tags become
  dense, literal signal for the embedder; the description adds the evocative coverage.
- **It only assembles what it's given.** Its quality is capped by the quality of `enriched` — so
  the way to improve the embedded text is to feed it a better description (that's Synth's job),
  not to make Compose cleverer.

## How we measure it

Two angles:

- **Unit tests (deterministic).** Pin the contract exactly: the composed text contains the
  expected phrase for each field, empty fields are skipped, the order holds. No oracle needed —
  the output is fully determined (`tests/unit/RuleComposeEnricher/`).
- **As the retrieval baseline.** On the scorecard, the `rule` pipeline *is* Compose over raw
  data — so its Recall@K / inversions are the **zero-point** every other pipeline (curator,
  synth) is compared against. Compose isn't graded for "prose quality" (there's none); it's the
  ruler's origin, and the question is always *how much a better-fed Compose beats it*.

## Example: before → after

Real game — **Pandemic** (enriched fields after the upstream steps).

**Before** (the `enriched` record — fields + description):

```
name=Pandemic · players=[2,3,4] · duration=45 · complexity="Medio" (level 2)
tags=[Cooperativo, Gestione della Mano, Punto di Azione] · editore=Z-Man Games · anno=2008
description="Cooperativo: una squadra di specialisti gira il mondo per curare quattro
            malattie prima che le epidemie dilaghino."
```

**After** (the single `embed_text` string the embedder receives):

```
Pandemic
Si gioca da 2 a 4 giocatori.
Una partita dura circa 45 minuti (durata media, circa un'ora).
Complessità: Medio. Adatto a principianti e famiglie.
Meccaniche e temi: Cooperativo, Gestione della Mano, Punto di Azione.
Categoria: Giochi da tavolo. Editore: Z-Man Games. Anno di pubblicazione: 2008.
Cooperativo: una squadra di specialisti gira il mondo per curare quattro malattie prima che
le epidemie dilaghino.
```

The scattered structured fields become explicit sentences ("Si gioca da 2 a 4 giocatori",
"Complessità: Medio") that the embedder can match against natural queries. The same Compose,
once **Synth** rewrites that final description block, is how setting/genre/online facts will
enter this text.

## Potential improvements

All measurable on the retrieval scorecard (it's the ruler this step defines):

### 1. Trim constant prefixes, keep the informative leaf

`categoria` in the real catalog is a **hierarchy**, e.g. `Giochi da tavolo > Giochi Gestionali`.
The leading `Giochi da tavolo >` is constant across every game — pure dilution — but the **leaf**
(`Giochi Gestionali`, `Giochi di Avventura`, `Party Game`…) is strong **genre signal**. Compose
should drop the constant prefix and surface the leaf (it even pairs with the Curator's
"genre from category" idea — the leaf ≈ genre, the slot with the worst recall). Measurable on the
scorecard. *(Note: the bundled mock flattens `categoria` to a constant `"Giochi da tavolo"`, which
is unrealistic — the mock should mirror the real hierarchy so local tests aren't misleading.)*

### 2. Reorder toward the most-queried dimensions

The template currently leads with players/duration. But users mostly search by **theme, setting,
mechanics** — which today sit mid/late in the text and get diluted. Leading with the theme words
(and putting the structured housekeeping last) is pure representation engineering on the template,
testable as an A/B on the scorecard.

### 3. Surface `extracted` even without Synth

Compose ignores `game.extracted` today (only Synth would weave it in). A cheap deterministic
fallback: when Synth doesn't run, Compose could append the Curator's extractions as an explicit
line ("Tema/genere: …"), so at least the extracted signal reaches the embedding. A lighter
alternative to the full Synth path, comparable on the same harness.
