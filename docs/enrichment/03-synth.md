# Step 3 — Synth

**Status:** ✅ implemented (first version, under evaluation) ·
**Code:** `app/ingestion/enricher/synth.py`

> First measured result: the `curator → synth → compose` pipeline is the **first one to beat the
> raw baseline** on the `core` retrieval suite (higher recall *and* precision, fewer inversions)
> — the long-standing goal. The missing link works. Now we refine it.

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

## What it does

Take a game's material and rewrite it into a single, dense, search-friendly **descriptive**
synthesis:

- **`extracted`** (the Curator's quoted extractions: setting, genre, audience…),
- **web facts** (verified, with provenance, from step 2 — already in the description),
- **multi-source `source_descriptions`** (the other source texts — see step 1's improvement;
  the main description is the most *readable* one, not the most *informative*),
- **certain data** as *context only* (so the prose doesn't contradict it — not to be restated).

Output: `enriched.description` = a descriptive synthesis (short, dense), which then flows into
Compose (step 4) and becomes part of `embed_text`.

### Division of labor with Compose

A game's facts are produced by the layer that can do it most reliably, and **each fact appears
once**:

| Fact kind | Owner | Why |
|-----------|-------|-----|
| structured — players, duration, complexity, year, tags | **Compose** (deterministic, from fields) | always present, zero hallucination risk; the guarantee that "certain data wins" |
| descriptive — setting, theme, genre, audience, "what you do", web facts with no field | **Synth** (prose) | only an LLM can weave these into text; they're the actual retrieval weakness |

So Synth is told **not to restate the structured numbers** (Compose adds them separately) — that
avoids duplicating them in the embedded text. A little *thematic* overlap (a mechanic named in
both the tags line and the prose) is fine and even reinforces the signal; restating the numbers
is what we avoid.

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
- **Don't restate the structured numbers.** Players, duration, complexity and year are Compose's
  job (deterministic, from the fields). Synth writes the descriptive prose around them; it must
  not repeat the numbers, or they'd appear twice in the embedded text. Certain data is context:
  the prose must not contradict it.
- **It sees everything.** Its advantage over the old Curator-synthesis is precisely that it
  works over *all* the gathered material at once, not the main description alone.

## How we measure it

Two levels, because Synth has both a local goal and the end-to-end payoff:

1. **Retrieval scorecard (end-to-end)** — the real reason Synth exists, and the one already in
   place. The `synth` pipeline (`curator → synth → compose`) re-ingests the frozen `core` suite
   and is compared to the `rule` baseline on **Recall@K, Precision@K, inversions**. The bar:
   **beat the baseline** that the raw-data pipeline sets — the number every prior experiment
   failed to beat. The first version clears it; this is the verdict that matters. (The Web step
   is left out of the *offline* scorecard since it needs the network; it's measured separately by
   its own per-phase replay eval.)

2. **Fidelity eval (per-step)** — *not built yet* (see improvements). It would measure Synth in
   isolation against an oracle built from the input material: **coverage** (each input fact
   survives into the output — largely deterministic substring matching) and **no-invention** (the
   output asserts nothing absent from the input — the risky part of any generative step).

## Example: before → after

**Viticulture**, after steps 1–2 — the material Synth receives:

```
context (certain): players 1–6, duration 90 min, complexity medium, mechanics: worker placement
extracted        : (Curator) genre = gestionale
web facts        : (Web) ambientazione = Toscana   [source: goblins.net, quote "pre-modern Tuscany"]
sources          : main description (readable) + secondary source descriptions
```

**Before** (what gets embedded *today*, via Compose alone): the original main description — which
**never mentions Tuscany**. A search for *"gioco gestionale ambientato in Toscana"* can't find it,
even though we *did* recover the setting in step 2.

**After** (Synth output → `enriched.description` — note: *no* player count / duration / complexity;
those come from Compose):

```
Gestionale ambientato nella Toscana pre-moderna: a capo di una cantina vinicola si piantano
vigne, si raccoglie l'uva e si vinifica stagione dopo stagione per soddisfare gli ordini.
Piazzamento lavoratori dal tono pacato e gestionale, godibile anche in solitario.
```

Compose then prepends the structured facts ("Si gioca da 1 a 6 giocatori.", "Durata 90 min…")
deterministically. Together, the embedded text carries **setting (Toscana), genre, mechanics**
from Synth and **players, duration, complexity** from Compose — each once — the
facts that steps 1–2 worked to gather. The search can finally rank it for the queries that
matter.

## Potential improvements

The first version already beats the baseline; the leads to push it further:

- **Settle the structured/descriptive split in practice.** The first measured run still had some
  numeric overlap; the prompt now forbids it. Re-measure to confirm removing the duplication helps
  (less dilution) rather than hurts (the repetition was reinforcing signal).
- **Fix the regressions, not just the average.** The scorecard moved up on average but some
  individual queries got *worse* (e.g. auctions/bidding). The synthesis may be dropping a theme it
  shouldn't. Per-query diffs are the to-do list — a theme that regresses means Synth lost a word
  the baseline kept.
- **Different models.** Synthesis quality is the model's quality (and the no-invention discipline
  matters a lot here). Free A/B on the scorecard, like the other steps.
- **Multi-source wiring.** Feeding all `source_descriptions` (step 1's open question) gives Synth
  more material to fuse — measure whether it adds signal at scale.
- **Fidelity eval (not yet built).** The retrieval scorecard tells us it helps end-to-end, but we
  don't yet measure Synth *in isolation*: coverage (did each input fact survive?) and
  no-invention (did it add unsupported claims?). Worth adding, like the other steps' per-step evals.
