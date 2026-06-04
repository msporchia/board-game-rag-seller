# Step 3 — Synth

**Status:** 🚧 TODO — this file is a **design spec**, not documentation of existing code.
**Code:** not implemented yet (`app/ingestion/enricher/` has no `synth.py`).

## Why this step exists (the missing link)

Steps 1 and 2 do real work: the Curator pulls facts out of the text into `extracted`, the Web
step fills the remaining gaps with verified facts. **But today none of that reaches the text we
embed.** The final Compose step (step 4) builds `embed_text` only from the `enriched` fields —
the description and the tags — and **nobody writes the Curator's extractions or the Web facts
back into the description.** So setting, genre, audience, online-recovered facts… are computed
and then dropped.

This is exactly why enrichment does **not** beat the raw baseline on retrieval: the pipeline
gathers good signal and then throws it away before embedding.

**Synth is the step that fuses everything into the text we embed.** It sits after the Web step
and takes *all* the material we've accumulated, then writes one unified description that carries
the facts forward into `embed_text`. Without it, steps 1–2 are wasted; with it, the search
finally sees setting/genre/online facts.

## What it will do

Take **all available material for a game** and rewrite it into a single, dense, search-friendly
description:

- **certain data** (structured catalog fields — always wins),
- **`extracted`** (the Curator's quoted extractions: setting, genre, audience…),
- **web facts** (verified, with provenance, from step 2),
- **multi-source `source_descriptions`** (the other source texts — see step 1's improvement;
  the main description is the most *readable* one, not the most *informative*).

Output: `enriched.description` = a unified synthesis (~400–600 chars) built from **everything**,
not just the original main description — which then flows into Compose (step 4) and becomes part
of `embed_text`.

> **Rewrite, don't compress.** This is the hard-won lesson from the failed experiments
> (`docs/valutazione.md` §6): blindly *cutting* the description (trim) and *compressing* it
> (Curator v1's old synthesis) both **lost recall**, because the verbose prose carries theme
> words ("cooperativo", "fantasy", god names…) that *reinforce* the signal. The lever is not
> deletion — it's **rewriting**: keep the useful content, weave in the canonical facts, drop
> only the marketing noise.

## How we expect it to behave

- **Fuse, never invent.** Only facts present in the input material make it into the text — same
  anti-hallucination stance as the Curator and the Web step. The synthesis adds *structure*, not
  new claims.
- **Keep the signal words.** Theme/setting/mechanic words must survive (the trim lesson). Dense
  canonical facts (→ precision) + a little evocative prose (→ generalization: "medieval" should
  still catch castles/knights), kept **short** (→ less dilution).
- **Certain data wins.** If the catalog and a source disagree, the catalog wins.
- **It sees everything.** Its advantage over the old Curator-synthesis is precisely that it
  works over *all* the gathered material at once, not the main description alone.

## How we will measure it

Two levels, because Synth has both a local goal and the end-to-end payoff:

1. **Fidelity eval (per-step).** Does the synthesized text *faithfully* carry the input facts,
   and *only* those? Two checks against an oracle built from the input material:
   - **Coverage** — each canonical fact we fed in (setting, genre, players, mechanics…) should
     appear in the output. Missing facts = lost signal.
     *(largely deterministic: substring / normalized matching, like the Curator's slot scoring.)*
   - **No invention** — the output must not assert facts absent from the input. This is the
     risky part of any generative step; it needs an anti-hallucination check (and, where
     feasible, a verbatim/grounding link back to the material).

2. **Retrieval scorecard (end-to-end).** The real reason Synth exists. Re-run the frozen `core`
   suite with the full `curator → web → synth` pipeline and compare to the `rule` baseline on
   **Recall@K, Precision@K, inversions**. The target is simple: **beat the baseline** that the
   raw-data pipeline sets (the number every prior experiment failed to beat). This is the verdict.

## Example: before → after (target behaviour)

**Viticulture**, after steps 1–2 — the material Synth receives:

```
certain data : players 1–6, duration 90 min, complexity medium, mechanics: worker placement
extracted    : (Curator) genre = gestionale
web facts    : (Web) ambientazione = Toscana   [source: goblins.net, quote "pre-modern Tuscany"]
sources      : main description (readable) + secondary source descriptions
```

**Before** (what gets embedded *today*, via Compose alone): the original main description — which
**never mentions Tuscany**. A search for *"gioco gestionale ambientato in Toscana"* can't find it,
even though we *did* recover the setting in step 2.

**After** (target Synth output → `enriched.description`):

```
Gestionale di piazzamento lavoratori ambientato nella Toscana pre-moderna: gestisci una
cantina vinicola attraverso le stagioni — pianta vigne, raccogli, vinifica e soddisfa gli
ordini. 1–6 giocatori, ~90 minuti, complessità media. Ottimo anche in solitario.
```

Now the embedded text carries **setting (Toscana), genre, mechanics, players, duration** — the
facts that steps 1–2 worked to gather. The search can finally rank it for the queries that
matter. *(This is the intended output; the step doesn't exist yet.)*

## Open design decisions (to settle when we build it)

- **Output target.** Does Synth write `enriched.description` (and let Compose assemble the final
  `embed_text` from the fields — keeping Compose as the single text-ordering step), or does it
  produce the whole `embed_text` directly (an "LlmCompose")? Leaning toward the former, so the
  deterministic Compose stays the one place that controls word order.
- **Determinism vs cost.** It's an LLM step → slow and non-deterministic. Same playbook as the
  others: fake the LLM in unit tests (assert the contract), measure quality with the real model
  on a small frozen set, iterate with `EVAL_LIMIT`.
- **Multi-source wiring.** Whether to feed all `source_descriptions` here depends on step 1's
  open question (is the extra material worth it at scale?). Synth is the natural place to consume
  it once that's settled.
