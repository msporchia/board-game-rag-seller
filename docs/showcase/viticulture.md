# ⚖️ Viticulture — an honest regression we measured (and didn't hide)

> **Headline:** on a game that *already* has a rich description, the full pipeline ranks it
> **worse** than the plain baseline — **#4 → #23** on one common query. We found it with the
> end-to-end eval, wrote a test that asserts the *fixed* behaviour (currently `xfail`, red), and
> documented the cause. **This is the failure that justifies the whole e2e harness.**

A showcase that only shows wins is a sales brochure. The reason to trust the
[Terraforming Mars](terraforming-mars.md) result is that the same measuring rig also catches
the cases where the pipeline loses — and reports them.

```mermaid
flowchart LR
    DTO["① Rich DTO<br/>desc already says<br/>toscana · vino · vigna"] --> BASE["② Baseline<br/>rank 4 / 1<br/><i>strong</i>"]
    BASE --> SYN["③ Synth compresses<br/>~2300 → ~1200 chars<br/><i>drops vino · toscana</i>"]
    SYN --> RANK["⑤ rank 23 / 3<br/><i>worse</i>"]
    style BASE fill:#1f7a1f,color:#fff
    style RANK fill:#7a1f1f,color:#fff
```

---

## ① The raw input — a *rich* DTO

Unlike [Terraforming Mars](terraforming-mars.md), Viticulture's catalog record is already full
of the right signal:

```jsonc
{
  "name": "Viticulture Essential Edition - Gioco Strategico di Piazzamento Lavoratori, ...",
  "tags": ["Aste", "Coltivazione", "Economia", "Piazzamento lavoratori", "..."],
  "description": "… Immagina di essere immerso nella dolcezza della campagna toscana …
                  trasformare un semplice vigneto … raccogliere uve pregiate e trasformarle
                  in vini … diventare il maestro vignaiolo …"
  // ↑ already contains: toscana, vigneto, uve, vino, vignaiolo
}
```

The Curator confirms the setting **from the description itself** → no gap → the **Web step
correctly does not fire** (verified in [`e2e-findings.md`](../enrichment/e2e-findings.md)
§3). There's nothing to recover. So what could enrichment possibly add? On this game — *the
problem isn't what it adds, it's what it removes.*

## ② Baseline — already strong

The deterministic baseline (`rule`: Compose over the raw DTO, ~2300 chars) ranks Viticulture
near the top, because the rich description carries the theme words straight into the embedding:

| User query | Baseline rank |
|------------|:------------:|
| *"vendemmia / stagioni / vigna"* | **#4** |
| *"tenuta vinicola in Toscana"* | **#1** |

## ③ Where it goes wrong — Synth compresses instead of rewriting

Here's the catch: **the Web step is idle, but Synth still runs — it always does.** Synth isn't
gated on `missing_info`; it rewrites *every* game's description (its second job is stripping
marketing noise, not just fusing recovered facts). So even with nothing to recover, Viticulture
goes through Synth — and that's where it loses.

The Synth step caps the rewritten description at ~700 chars (`synth.py:_MAX_CHARS`). On a game
whose richness *was* the signal, that cap **compresses away** theme words the baseline had:

- full pipeline `embed_text` ≈ **1200 chars** vs baseline ≈ **2300 chars**;
- a keyword count (substring — a *hypothesis for why*, not the vector's verdict) shows the full
  text **losing** `vino` / `toscana`.

This is the exact risk written into the [Synth design doc](../enrichment/03-synth.md):
*"rewrite, don't compress."* The lesson from earlier failed experiments was that verbose prose
carries reinforcing theme words — blindly cutting it loses recall. Synth's first version still
falls into that trap on already-rich games.

## ⑤ The measured regression

| User query | Baseline | **Full pipeline** | |
|------------|:--------:|:-----------------:|---|
| *"vendemmia / stagioni / vigna"* | #4 | **#23** | 🔻 worse |
| *"tenuta vinicola in Toscana"* | #1 | **#3** | 🔻 worse |

The game **slips out of the first screen** on a perfectly common query. On a thin catalog this
trade is invisible (there's no rich text to lose); on a rich one it's a real regression.

## How we treat a finding like this

This is where the engineering discipline shows. The failure isn't a footnote — it's wired into
the test suite:

1. **A test asserts the *fixed* behaviour, marked `xfail`** —
   `test_phase3_retrieval::test_synth_does_not_degrade_rich_dto`. It's red today and will turn
   green when Synth stops compressing. The suite *expects* the bug until it's fixed, so a real
   fix is provable and a regression can't sneak back.
2. **The cause is written down**, with the measured numbers, in
   [`e2e-findings.md`](../enrichment/e2e-findings.md) §1.
3. **The fix direction is scoped**: calibrate Synth's budget to the embedder's real useful
   capacity, and never drop below the baseline's thematic signal ("rewrite, not compress").

And a note on **how much it matters**: per the project's *first-screen* philosophy, the vector
search is a coarse filter (return ~10–20 of N), and a later LLM step re-reads the candidates in
full. Some lost keywords (e.g. `oceani`) aren't realistic user queries, so losing them costs
little. But `toscana` / `vino` on Viticulture **are** common queries — so this one counts, and
stays open.

→ Back to the [pipeline overview](../enrichment/README.md) · the [other walkthroughs](README.md).
