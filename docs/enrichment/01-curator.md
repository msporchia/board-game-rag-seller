# Step 1 — Curator

**Status:** ✅ implemented · **Code:** `app/ingestion/enricher/curator.py`

## Why this step exists

The source catalog is **messy and heterogeneous**. Not every game has every characteristic
filled in: some come with clean structured fields, others have nothing but a wall of marketing
prose, and the useful facts are scattered — some in catalog fields, some buried in the
description, some only in one of several source texts, some missing entirely.

If we hand this raw mess straight to the downstream steps, they handle it badly: the Web step
wouldn't know what to actually look for, Synth wouldn't know what material it has, and at
retrieval time games with gaps get **mis-weighted, silently dropped, or compared on unequal
footing** with the well-described ones. Heterogeneous input produces heterogeneous, unreliable
output.

The Curator's job is to **impose a uniform structure on this mess before anyone depends on
it**. For every game — rich or thin — it answers the same three questions: *what do we reliably
know, what can we recover from the text, and what is genuinely missing?* That uniform map is
what lets every later step act surgically instead of guessing: the Web step fetches only the
real gaps, Synth knows exactly what it can fuse, and retrieval works on **curated, comparable
records** instead of raw noise. In short: this step exists to **curate a messy dataset so the
rest of the pipeline can trust it.**

## What it does

Concretely, the Curator is a **focused LLM pass** that, for each game, produces that map:
**what we already know, what can be pulled out of the description, and what is missing.**
It does *not* rewrite the description and it does *not* invent — its only job is to read the
text and classify/extract.

It reasons over **7 key pieces of information**, in two families:

| Family | Info | Where it comes from |
|--------|------|---------------------|
| **Descriptive** (3) | setting/theme, genre, who it's for | never in the catalog → **always** asked to the LLM |
| **Structured** (4) | mechanics, player count, duration, complexity | have a catalog field → asked to the LLM **only if missing** |

The output is a stable verdict per game: `{extracted, present, missing}`.
- **present** — info we have (from the catalog, or successfully extracted from the text).
- **extracted** — descriptive facts pulled from the description, kept for later synthesis.
- **missing** — info we couldn't confirm anywhere → this becomes the shopping list for the
  **Web** step (step 2): "go online only for what's actually missing".

## How we expect it to behave

- **No invention.** If the description doesn't state the setting, the slot must end up
  *missing* — not guessed from the vibe. This is the single most important behavior.
- **Certain data wins.** Structured facts already in the catalog are taken as-is; the LLM is
  never even asked about them (on real catalogs they're present ~49 times out of 50, so asking
  would only add load and risk to a small model). We re-apply them ourselves, downstream.
- **Every extraction is backed by a verbatim quote.** The LLM must copy the exact phrase from
  the description that justifies a value. We then **check the quote is really in the text**; if
  it isn't, the extraction is thrown away (it was fabricated) and the slot falls into *missing*.
- **Precision over recall.** A wrong extraction pollutes the data — worse than leaving a slot
  empty. We'd rather miss than guess.

## How we measure it

This is a **classification + extraction** task, so we score it like one — the standard
slot-filling metric (the same idea used in information-extraction benchmarks). For each of the
7 slots, comparing the Curator's output to the oracle, the outcome is one of:

| Outcome | Meaning |
|---------|---------|
| **TP** | extracted, and the value matches the answer key |
| **FP** | extracted, but wrong (or the slot should have been empty) — *invention* |
| **FN** | marked missing, but the answer key had a value — *a miss* |
| **TN** | marked missing, and the answer key agrees it's absent |

These aggregate into **Precision / Recall / F-score**. We report F-β with β < 1 (F0.5, F0.25),
which weighs a false positive **4× / 16× more** than a false negative — because, again, a
polluted field hurts more than a gap.

The oracle (`tests/eval/CuratorEnricher/fixtures/assess_cases.json`) is hand-written per game:
each slot is either a list of acceptable substrings (gold *present*), `null` (gold *absent* —
any extraction is an FP), or "already in the catalog" (skip — not the Curator's job). It is
**partial on purpose**: we only assert what we're confident about.

> The run prints Precision/Recall/F-β plus a per-slot TP/FP/FN/TN breakdown, and saves a
> timestamped report so we can see the **delta vs the previous run** (catching regressions when
> we change the prompt or the model). Iterate fast with `EVAL_LIMIT=2`.

## Example: before → after

Real catalog game — **"Dungeon Saga: La Missione del Re dei Nani"**.

**Before** (what the Curator receives): the raw catalog record.
- *Description* (marketing prose): *"…con questo straordinario gioco da tavolo **fantasy**,
  potrai esplorare **dungeon** oscuri e affrontare nemici temibili insieme ai tuoi amici…"*
- *Structured fields*: duration = 120 min, complexity = "Medio-Leggero", **player count
  empty**, mechanics present.

**After** (the Curator's verdict):

| Slot | Verdict | Why |
|------|---------|-----|
| setting/theme | ✅ extracted → **"fantasy"** | quoted verbatim from the text — correct |
| mechanics, duration, complexity | ✅ present (from catalog) | certain data, LLM not even asked |
| player count | ⊘ missing | empty in the catalog *and* no explicit number in the text → correctly left missing |
| genre | ❌ missing (should be "adventure/co-op") | the text implies it, but the LLM found no quote it would commit to — **a miss (FN)** |
| who it's for | ⚠️ extracted → **"families"** | nothing in the text says this — **a fabricated default (FP)** |

So this game scores **1 good extraction, 1 correct gap, 1 miss, 1 invention** — a compact
picture of both the strength (no fantasy/dungeon hallucination, player count honestly left
blank) and the two failure modes we track: **missed genre** and the **"families" default**.
The metric turns these per-slot outcomes into a single number we can push up over time.

## Potential improvements

The two failure modes above — **missed genre** (low recall) and **invented audience** (the
"families" default) — are where there's room to grow. Some leads, each measurable on the same
slot-filling harness (run before/after, read the delta in the saved report):

### 1. Use all the source descriptions, not just the "best" one

The source doesn't give us one description per game — it gives **several, one per source**, and
each is written differently. What arrives as the main `description` is the text from the source
we consider to produce the **best** descriptions — but "best" here means *most readable / most
curated*, **not** *most informative*. A cleaner write-up can easily contain **fewer facts** than
a rougher one.

The Curator today reads **only** that main description. So when the readable source happens to
omit a fact, the Curator has no way to recover it — even though another source states it plainly.

Real example — **Catan** (`source_descriptions` in the catalog):

```
main description : "Gioco di gestione risorse e commercio: raccogli materie prime,
                    costruisci strade e villaggi e negozia con gli altri…"
[source: fonte2] : "Classico tedesco di negoziazione e gestione risorse,
                    ottimo per famiglie."        ← states the audience the main text omits
```

The audience slot ("who it's for") is exactly the one the Curator gets wrong by defaulting to
"families". Here a *different source literally says it* — so feeding all sources would let the
Curator extract it **with a verbatim quote** instead of inventing it. More material → more facts
recoverable with evidence → higher recall *and* fewer fabricated defaults.

Status: the field exists in the original source and the helper to gather it
(`_collect_descriptions`) is already written, but `assess()` does **not** use it yet — and the
test fixtures predate the field, so they don't carry it. Before wiring it in, the value should
be **measured at scale** (on a real catalog: how often does a secondary source actually add a
fact the main one lacks?), to confirm it's worth the extra tokens.

### 2. Try different models

The extraction quality is the model's quality. Different LLMs have **different strengths** — some
are stronger on Italian, some on disciplined structured extraction, some on instruction-following
under "don't invent" constraints. The current baseline is `llama3.1` (8B); models like Qwen2.5 or
Gemma may trade differently between the precision/recall axes we care about.

This is low-hanging because the harness already makes it an A/B: swap the model, re-run the eval,
and the saved report shows the per-slot delta vs the previous run. No code change beyond the model
name — just measure which model wins on *our* slots and *our* precision-favored weighting.

### 3. Derive genre from the catalog category

The catalog's `categoria` field (a sub-category) is almost always present and often maps cleanly
to genre — which is the slot with the worst recall. Deriving genre from it (as certain data,
bypassing the LLM) could cut the genre misses without any extraction risk. To be measured like
the rest.
