# Experiments ledger — one row per change, before → after

Protocol: every lever (embedder, compose template, k, model) is measured on the SAME frozen
rulers before/after, and the delta is recorded here the moment the run finishes. No number,
no claim.

## Rulers (the fixed measuring sticks)

| Ruler | Command | Measures | LLM in loop |
|-------|---------|----------|-------------|
| Suite scorecard | `docker compose exec seller-api python -m tests.eval_suite --suite core --k 5 --pipeline rule` | Recall@5, Precision@5, err (≈1−AUC) over 12 queries × 50 frozen games | none (rule pipeline is deterministic) |
| Ranking NDCG | `docker compose exec seller-api python -m pytest tests/eval/GameRetriever -q` | per-case NDCG over the frozen *enriched* corpus (`games_enriched.json`) | none (enrichment frozen at freeze time; only embedder + Qdrant live) |
| Chat retrieve | `docker compose exec seller-api python -m pytest tests/eval/ChatRetrieve -q` | recall of the conversational query assembly | yes (intent LLM) — secondary, noisier |

> ⚠️ Bitrot found 2026-07-03: the documented `python -m tests.eval` no longer ran — the
> `tests/eval/` package shadowed `tests/eval.py`. **Fixed the same day**: the script is now
> [`tests/eval_suite.py`](../tests/eval_suite.py) (`python -m tests.eval_suite`, no PYTHONPATH
> workaround), and every doc that named the old entrypoint was updated with it.

## Watch cases (the queries the next lever must move)

- `coop-famiglia-figli` — NDCG **0.132**, Pandemic ranks #6/#5 (outside k=5)
- «mondo antico, Grecia o Roma» — R@5 **0.00**, first relevant at #11
- «combattimento» — R@5 **0.09**
- «esplorazione e avventura» — R@5 **0.11**

## Ledger

| # | Date | Change | Ruler | Before | After | Verdict |
|---|------|--------|-------|--------|-------|---------|
| 0 | 2026-07-03 | *(baseline re-run, no change)* — `nomic-embed-text`, pipeline `rule` | Suite scorecard | R@5 0.26 · P@5 0.42 · err 0.32 (historical) | R@5 **0.25** · P@5 **0.40** · err **0.32** | ✅ ruler reproduces — trustworthy |
| 0b | 2026-07-03 | *(baseline re-run, no change)* — `nomic-embed-text`, frozen enriched corpus | Ranking NDCG | mean 0.386 (historical) | 12 cases recorded, coop 0.132, best 0.922 | ✅ ruler reproduces |
| 1 | 2026-07-03 | **embedder swap `nomic-embed-text` → `bge-m3`** (env override only, prod index untouched) | Suite scorecard | R@5 0.25 · P@5 0.40 · err 0.32 | R@5 **0.43** · P@5 **0.67** · err **0.20** | 🚀 biggest single lever ever measured (+72% recall) — SEL-107 hypothesis confirmed |
| 2 | 2026-07-03 | same swap, second ruler | Ranking NDCG | mean 0.386 · displacement 10.68 · perfect 0/12 | mean **0.701** · displacement **3.51** · perfect 1/12, close(≥0.8) 5/12 | 🚀 confirmed. «treni-famiglia» 0.00→**1.00**, «tessere-medioevo» 0.00→0.82, «mondo antico» 1st-rel #11→**#1**, «cooperativo» R@5 0.17→0.67 |

### Row 1-2 detail — what bge-m3 did and did not fix

Fixed (thematic/semantic axis): ancient-world, trains, tiles/medieval, exploration, fantasy —
the Italian-language blindness of `nomic` was the dominant failure mode.

**Not fixed (mechanic axis): `coop-famiglia-figli` only 0.132 → 0.210** (Pandemic still #9/#3/#6,
one outside k=5). Cooperative is a *mechanic*, weakly present in prose — this is exactly what the
SEL-142 structured filter is for (currently inert: `cooperative=None` on all 501 stored products;
backfill needed). Embedder and filter are complementary levers, not alternatives.

> ⚠️ Caveat: `tests/eval/GameRetriever/RESULTS.md` + `runs/` got auto-overwritten by the bge-m3
> session without recording which embedder was live (exactly the SEL-102 gap). Historical nomic
> numbers survive in this ledger and in git history.

| 3 | 2026-07-03 | **bge-m3 promoted to default** (`app/config.py`, `docker-compose.yml`, `.env.example`) + live `games` collection re-embedded from stored `embed_text`s (501 products, embed-only, no LLM re-run) | live `/search` smoke | «antica Grecia» → generic hits | «antica Grecia» → **Lords of Hellas #1, Santorini #2** | ✅ SEL-107 resolved; ADR-0001 annotated (Revisited) |
| 4 | 2026-07-03 | *(probe, no change)* — Terraforming Mars on the **suite corpus** (rich DTO, 1.6k-char description), raw `rule` text, 3 showcase queries | ad-hoc rank probe | showcase baseline **#45/#47/#47** | nomic today: **#1/#35/#1** · bge-m3: **#1/#4/#1** | ℹ️ not a contradiction: the showcase's #45 was measured on the **deliberately stripped** DTO (`tests/e2e/enrichment`, description removed) — the piloted thin-record scenario the pipeline exists for. The suite DTO is rich, so it ranks #1 even raw. Lesson recorded: the walkthrough should state explicitly that its baseline uses the stripped record, or a skeptical reader "re-checking" it on the suite corpus concludes it's fake. |

### The question row 4 leaves open — "does the Synth still earn its keep under bge-m3?"

Measured (rows 5-6 below). The full matrix, suite `core` (K=5):

| Recall@5 (P@5 · err) | nomic | bge-m3 |
|---|---|---|
| `rule` (no LLM) | 0.25 (0.40 · 0.32) | **0.43 (0.67 · 0.20)** |
| `synth` (full enrichment) | 0.28 (0.48 · 0.25) | 0.40 (0.60 · 0.21) |

| 5 | 2026-07-03 | *(measurement, no change)* — `--pipeline synth` under bge-m3 (llama3.1 synth, ~7 min GPU) | Suite scorecard | rule/bge: R@5 0.43 · P@5 0.67 | synth/bge: R@5 **0.40** · P@5 **0.60** · err 0.21 | ⚠️ under bge the synth is **net negative in aggregate** (was net positive under nomic). High per-query variance: «cooperativo» 0.67→**0.83** (P 1.00, err 0.00 — first clean query ever), «gestione economica» +0.10, but «piazzamento lavoratori» 0.27→**0.09** (P 0.60→0.20), «combattimento» −0.09, «esplorazione» −0.11 |
| 6 | 2026-07-03 | *(measurement, no change)* — `tests/e2e/enrichment` stripped-source scorecard under bge-m3 | e2e regression gate | nomic era: stripped TM ranked **#45/#47/#47**, enrichment → #1/#26/#1 | stripped TM (no description) already at avg rank **2.33** un-enriched; enrichment → **1.33**; Viticulture regression gone (1.67→1.0); gate green | ℹ️ the gap enrichment used to close has shrunk from "#45→#1" to "2.33→1.33": bge reads the informative *name* + tags alone. Enrichment's unique remaining value: mechanic axes (structured fields/filters), truly opaque records, provenance |

**Diagnosis (probe on the synth-written `embed_text`s):** the mechanic terms are NOT lost — the
tag line («Meccaniche e temi: … Piazzamento lavoratori …») is written by the deterministic
Compose and survives intact. What hurts is the synth *prose*: llama3.1 produces homogeneous
"gioco strategico dove i giocatori…" boilerplate across games, so games become mutually
confusable and mechanic-specific queries lose precision. The synth doesn't drop facts — it
**flattens distinctiveness**. (Caveat: synth texts are regenerated per run, so the nomic-column
synth numbers come from a different generation of texts.)

| 7 | 2026-07-03 | *(measurement, no change)* — `rule-uncapped`: full original description (median 2.9k chars, no 1800 cap), zero LLM | Suite scorecard | rule/bge: R@5 0.43 · P@5 0.67 · err 0.20 | R@5 **0.39** · P@5 0.60 · err 0.19 | ⚠️ "give the strong embedder everything" **falsified**: dilution survives bge, just weaker. «piazzamento lavoratori» crashes to 0.09 here too → the mechanic-axis crash is caused by *prose mass*, not by synth prose specifically |
| 8 | 2026-07-03 | *(measurement, no change)* — `synth-append`: full description + fused synth layer on top (uncapped compose) | Suite scorecard | synth-replace/bge: R@5 0.40 · P@5 0.60 · err 0.21 | R@5 **0.41** · P@5 0.65 · **err 0.18 (best ever)** · coop clean 0.83/1.00/0.00 | ✅ append ≥ replace on every aggregate; keeps the coop win. But «mondo antico» 0.75→0.50 and WP 0.18: prose mass still taxes narrow axes |

### The four-cell text-budget picture (bge-m3, suite `core`)

| variant | embed chars (typ.) | R@5 | P@5 | err |
|---|---|---|---|---|
| `rule` (cap 1800) | ~2.4k | **0.43** | **0.67** | 0.20 |
| `rule-uncapped` | ~3.5k | 0.39 | 0.60 | 0.19 |
| `synth` (replace) | ~1.3k | 0.40 | 0.60 | 0.21 |
| `synth-append` | ~4.2k | 0.41 | 0.65 | **0.18** |

Honest readings (12 queries, 50 games — aggregate deltas of ±0.02-0.04 are ~1-2 hits, treat as
weak signal; the *per-axis patterns* replicate across variants and are the robust signal):

1. **Saturation is semantic, not token-based.** bge's window is 8k tokens; returns invert
   already around ~2-2.5k chars. More prose beyond that dilutes the centroid even for a strong
   embedder. The nomic-era 1800 cap is accidentally near the sweet spot.
2. **What the synth loses when the source is already rich: ~1-2 hits aggregate, in exchange for
   the coop axis going clean** (0.83/1.00/0.00 in both synth arms — its explicit «cooperativo,
   tutti insieme contro il gioco» sentence is worth more than 1k chars of marketing).
3. **The anti-fluff value is real but positional truncation is a crude tool**: the cap cuts
   concept-bearing sentences too («la collaborazione è fondamentale» sits at char ~1850 of
   Massive Darkness — `rule` never embedded it; the synth, which reads the FULL description,
   smuggled it back in. Part of the synth's coop win is *working around the cap*).
4. **Mechanic axes (worker placement) lose to prose mass in every variant** — best under the
   tersest text (rule 0.27), worst under the longest. Prose cannot carry that axis: it belongs
   to structured signal (tags → filters/boost; the piloted/agent engines already emit filters,
   and the cooperative flag exists precisely for this — pending backfill).

**Options on the table** (in ROI order):
1. **Prompt fix**: forbid generic boilerplate, mandate weaving the game's distinctive
   mechanic/theme terms into the prose (the material already contains them). → *done, row 9*
2. **Deterministic floor**: a variant where Compose appends `extracted` facts as terse labeled
   lines, no LLM — if it matches synth under bge, the merge channel survives at zero LLM cost.
3. **Stronger synth model** (SEL-109 / strong-model simulation): same prompt, measure whether
   the flattening is a model limitation or a prompt limitation.
4. **Harsher showcase scenario**: strip descriptions of *opaque-named* games (Onitama-like) so
   the walkthrough demonstrates recovery the embedder genuinely cannot do alone — the
   TM «#45→#1» headline is a nomic-era number and must be retold under bge.

| 9 | 2026-07-03 | **Synth v2 (SEL-144)**: budget 700→1600 + prompt v2 (searchable-concepts checklist, ban on could-be-any-game phrasing); replace mode kept by design | Suite scorecard + e2e gate | synth v1: R@5 0.40 · P@5 0.60 · err 0.21 | R@5 **0.43** · P@5 0.65 · err **0.19** · coop 0.83/**1.00**/err 0.02 · storytelling 0.40→0.60 · e2e gate green (TM recovery 2.33→1.33 intact) | ✅ criterion "≥ rule (0.43)" met: the normalizer now costs ZERO aggregate and buys the coop axis (0.83 vs rule's 0.67). Criterion "coop err 0.00" missed on the letter (0.02, one deep inversion; top-5 perfect). Chronic residuals delegated: WP 0.18 & aste 0.14 → structured signal (SEL-142 backfill) / stronger model (SEL-109). Homogeneity metric proved non-diagnostic (v2 0.594 ≈ rule 0.595) |
| 10 | 2026-07-03 | *(re-baseline, no change)* — ChatRetrieve (conversational query assembly) under bge-m3 | ChatRetrieve eval | recall@k **0.545**, mean rank 1.33 (nomic era) | recall@k **1.000** (11/11 found), mean rank 1.73 | 🚀 the June bottleneck («retrieval buries the only coop game») is gone at the retrieval layer: `pandemic-regalo-cooperativo` rank 1/k=2. Part-2 numbers were all nomic-era — full ChatConversation re-baseline follows |
| 11 | 2026-07-03 | *(measurement integrity)* — ChatConversation single-run re-baseline under bge exposed a **rigged bench**: in `horror-cooperativo` the agent correctly emits `cooperative: true` and gets **0 hits both turns** — the frozen corpus had no `cooperative` field at all. Regenerated `games_enriched.json` with the current pipeline (curator coop-verdict + synth v2) | corpus freeze | `cooperative` ABSENT ×50 | **27 False · 19 True · 4 None** (honest abstentions) | ✅ every eval on the frozen corpus (GameRetriever, ChatRetrieve, ChatConversation) re-baselines from here. Caveat also recorded: ChatConversation case-pass has huge run-to-run variance (agent scored 0.60/0.80/0.87 on identical June runs) — single-run deltas are NOT evidence; N-run repetition needed before claiming engine-level effects |
| 12 | 2026-07-03 | **First-ever live coop backfill** (SEL-142 flag on the 501-product store + Qdrant payloads, no re-embed) — then a spot-check exposed **SEL-145**: COOP_INFER precision 0.33 vs hand oracle (Ticket to Ride, Talisman, Dixit classified cooperative) | backfill + oracle mini-eval | `cooperative=None` ×501, coop filter returns 0 games | v1 12 FP → v2 6 FP → **v3 (abstention-first + verbatim-proof validated in code) 2 FP, 42/50 abstentions, 0 wrong False across all configs** | ✅ SEL-145 resolved under the zero-error rule — **as an accepted stopgap** (recall on untagged co-ops parked; revisit = SEL-146), per direction: **True = catalog only** (v3's 2 residual FPs include marketing that literally lies about team play — no validation survives a lying source); **False = inference allowed** (0 errors in 62 verdicts); rest None. Data realigned live+frozen. Live smoke: family-coop query + hard filter → 5/5 genuinely cooperative |
| 13 | 2026-07-03 | *(final re-baseline on the committed state)* — corpus re-frozen (synth v2 + coop policy), all rulers re-run | all | pre-refreeze snapshots | NDCG mean **0.726** (displacement 2.82) · ChatRetrieve **0.818** · ChatConversation pipeline **0.667** / agent **0.733** (both coop cases pass in the agent arm) | ℹ️ the committed numbers photograph the committed tree. Two honest wiggles: ChatRetrieve 1.000→0.818 (corpus texts changed under it) and `coop-famiglia-figli` semantic-only NDCG → 0.00 — the cooperative axis now lives on the STRUCTURED path (filter), exactly as rows 5-12 predicted; the prose ranking is no longer its carrier |
| 14 | 2026-07-03 | *(measurement, no change)* — **strong-model simulation, agent arm (SEL-109 / WP1)**: every LLM role answered by Claude Sonnet 5 through the file-exchange harness (commit e23c7c0); same engine, retrieval, frozen corpus and oracle as row 13 | ChatConversation (sim) | qwen2.5:7b agent **0.733** (11/15; run-to-run variance 0.60/0.80/0.87) | **15/15 (1.000)** · convergence 13/13 · turn oracles 5/5 · fallback/turn 0.062→**0.000** · 99 LLM calls vs 81 (more search retries, incl. recovery from one live retrieval 500) · mean turns-to-converge 1.46 | 🚀 above every run of the baseline's variance band: the 3 non-convergences + the `min_games` miss all disappear. Transcript audit: zero turns without a tool call; "cooperativo" uttered only about card-verified co-ops; no undeclared numeric filters spotted (players left null on "tre o quattro"). Caveats: single sim run vs stochastic baseline; filters_ok/proposal_ok oracles not in scope in the agent arm, so (b)/(c) rest on transcript audit, not oracle; responder ≫ any deployable local model — this measures the engine's ceiling ("the 8B is the bottleneck, not the harness"), not a shippable config. First attempt aborted at case 15: >900s responder-coverage gap tripped the reply timeout (fallback pitch fired) — rerun clean with `--timeout 3600`; ops note: keep responder coverage continuous or raise the timeout |
