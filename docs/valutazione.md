# How embedding works and how we measure retrieval quality

This document explains the mental model of embeddings and the methodology we use to evaluate
(and improve) semantic search, so we decide with numbers instead of by intuition.

## 1. How embedding works (mental model)

- **Fixed-size vector = lossy compression.** The embedding model (`nomic-embed-text`) always
  produces the same number of values (768) whether from 5 words or 2000. It compresses Y
  pieces of information into X numbers: it's an *information bottleneck*, lossy.
- **The vector is the text's "semantic centroid".** It doesn't intelligently choose what to
  keep: it represents the *dominant* meaning. If the description has three paragraphs of
  marketing ("epic legendary adventure") and half a line about "Greek mythology", the centroid
  leans toward "epic adventure" and the Greek detail gets **diluted**.
- **The embedder is query-agnostic.** It has general language knowledge but **does not know
  what the user will ask**. It compresses toward a generic idea of "what the text is about",
  which may not match our questions. No guarantee it embeds exactly the data we need.

## 2. The most important lever: the data, not (only) the embedder

We **know the distribution of the questions** (players, duration, setting, tone, "like X").
That's domain knowledge the model lacks, and that we can **inject** by shaping the text to
embed — *representation engineering*.

Two distinct levers:

| Lever | What it changes |
|------|-------------|
| **Embedder** (e.g. `nomic` → `bge-m3`) | how well it maps the *same* text |
| **Data quality/shape** (enricher) | *what* we give it to map |

Right balance of the text to embed: **dense canonical facts** (concentrated signal →
precision) **+ a bit of evocative prose** (→ generalization: "medieval" must catch
castles/knights), all **short** (less dilution). Often cleaning/concentrating the data moves
the needle more than changing the model: a smart representation beats brute force.

Example (Lords of Hellas):

```
BEFORE (embedding ~400 words of marketing):  centroid ≈ "epic adventure"
AFTER  (terse facts + tight synopsis):       centroid ≈ "Greek mythology + management"
  "Gestionale strategico competitivo, ambientato nella MITOLOGIA GRECA antica
   (Zeus, Atena, mostri). 1-4 giocatori, ~75 min, complessità media.
   Meccaniche: controllo aree, piazzamento lavoratori, combattimento eroico."
```

## 3. The score is NOT a "% of relevance"

Cosine similarity is **uncalibrated**: `0.7` does not mean "70% on topic". The scores sit in
a very narrow band and depend on query/model/language. Real numbers:

```
"cooperativo fantasy"  → Descent          0.698   ← great match
"mitologia greca"      → Terraforming Mars 0.639   ← WRONG match
```

~0.06 difference between perfect and wrong → a **fixed absolute threshold** (e.g. "70%") is
useless. The absolute number, alone, doesn't tell whether the information is embedded.

## 4. How we really measure: rank, not absolute score

The measure is **relative**, and it's robust precisely because it sidesteps the uncalibrated
scores.

- **You need distractors.** With a single game in the DB the top-1 is always it, whatever the
  score → it measures nothing. The distractors are the *ruler*. The question isn't "does it
  find it?" but "does it find it **before** the wrong games?".
- **Method (anchor + questions).** We pick a few **anchor games** we know perfectly, feed
  them the **raw DTO from the API**, and for each ask ~10 questions that characterize it
  (setting, players, duration, mechanics, tone, author, "like X"). Verdict: **does the game
  appear in the top-K?**
  - If yes → that information *is* embedded and findable.
  - If no → that dimension isn't embedded (diagnostic: we know *what* is missing).
- **Metrics.** `hit@K` (how many questions put the anchor in the top-K) and `MRR@K` (how high
  it gets). A single number to track to see if we improve or **regress**.
- **Diagnostics.** For each question we also report the actual rank and raw score (e.g.
  "rank 12, s=0.55"): useful to understand, but the **verdict stays the rank**.

> Alternative without distractors (idea to keep): **discrimination margin**. For a single
> game, compare the score of a query that *should* match with control queries that *should
> not*. If it doesn't separate them → info absent. The gap is the measure, per single game.
> (For now we use rank vs distractors.)

## 5. The three levers compete on the SAME harness

Order of work: first the ruler, then the levers.

1. **Baseline**: raw data + `nomic`.
2. **+ Enricher**: canonical facts in the text → re-measure hit@K/MRR.
3. **+ Embedder** (`bge-m3`): same set → re-measure.

This way we know *with numbers* what each move is worth, instead of guessing.

## 6. Measured baseline (suite `core`, raw data + `nomic-embed-text`)

First measure, to beat (50 games, 12 per-aspect queries, K=5):

```
Recall@5 = 0.26 | Precision@5 = 0.42 | avg inversions = 109 | queries with no inversions = 0/12
```

Highlights:
- "mondo antico, Grecia o Roma" → **Recall@5 = 0.00**, first relevant only at **#11**
  (diagnostic case: the setting is buried in the marketing).
- "fantasy" / "combattimento" / "esplorazione" → recall 0.09–0.17 (theme diluted).
- "storytelling" the best (R@5=0.60, 17 inversions).
- Precision often > Recall (e.g. worker placement P@5=0.80, R@5=0.36): when a relevant one
  surfaces it is on-topic, but it loses many → dilution hides the others.

Diagnosis: the discriminating facts (setting, theme, mechanics) are not well embedded →
motivates the enricher. It's the number to beat.

> Note: inversions are normalized to `err` ∈ 0..1 (fraction of relevant/irrelevant pairs
> mis-ordered, ≈ 1−AUC). Baseline `rule`: avg err 0.32.

### Experiment: trim — hypothesis FALSIFIED

Comparison on the `core` suite (K=5):

```
rule (deterministic compose)             Recall@5 0.26 | P@5 0.42 | err 0.32
trim (shortened description + compose)   Recall@5 0.19 | P@5 0.32 | err 0.46  ← WORSE
```

The hypothesis "marketing dilutes → cutting it helps" is **false** in this setup: the verbose
prose contains theme words (cooperativo, fantasy, names of Greek gods…) that **reinforce** the
signal; cutting it loses recall. Lesson: the lever isn't *removing* text (deletion) but
**rewriting** it, keeping the useful content and weaving in the canonical facts →
`LlmComposeEnricher`. The harness avoided a regressive "optimization".

## 7. Harness structure

```
seller/tests/
├── fixtures/
│   ├── games.json       # ~200 REAL DTOs from the API (anchor + distractors), reproducible
│   └── questions.json    # 4 anchors × ~10 questions (with expected id)
└── eval.py               # ingest into collection 'games_test' + scorecard (hit@K, MRR, rank+score)
```

- **Qdrant isolation**: the eval uses a dedicated collection `games_test` (override on
  `GameVectorStore`), recreated every run (`recreate=True`) → clean slate. The production
  collection `games` is never touched. (In CI you can also use in-memory Qdrant.)
- **Reproducible source**: `JsonSource` gives the system "exactly the API DTO" from a file,
  without depending on a running PrestaShop.
- **Run**: `docker exec seller-api python -m tests.eval_suite --k 5`.

Current anchors: Lords of Hellas (Greek mythology, management), Onitama (abstract, 2-player
duel), Massive Darkness (coop fantasy dungeon crawler), Dixit (party/storytelling). The
anchor/question net grows as we find cases the system gets wrong.

## 8. Robustness: the changing corpus (IR/TREC best practice)

The test "MY game must be in the top-K" is **fragile**: if I add a game (because a case gave
me trouble) and it is *also* relevant to the query, it pushes the target down a notch and the
system "looks broken" while being correct. Relevance must be treated as a property of the
(query, game) pair, with multiple relevant games per query.

Standard solutions:

- **Qrels with graded relevance**, not a single target: for each query you label the *set* of
  relevant games, on a 0–3 scale (irrelevant → perfect).
- **Set/graded metrics**: **Recall@K** (order-unaware, tolerates which relevant is #1),
  **nDCG@K** (graded + position discount, the standard), MAP, MRR. You no longer evaluate
  "the exact rank of the target".
- **FIXED, versioned corpus**: models are compared only at a fixed corpus. Adding a game = a
  new version of the dataset (corpus + qrels) → re-baseline and trend.
  *"Freezing versions keeps results comparable."*
- **Unjudged docs → pooling / LLM-as-judge**: you don't label 200×N pairs by hand; TREC uses
  pooling (you judge the union of the top-K of the various systems). Scalable with an
  LLM-judge validated on a human sample. ⚠️ Don't use the same LLM as ranker and judge (bias);
  topic-specific classifiers sometimes beat the raw LLM.
- **Two levels**: (a) aggregate metric (nDCG/Recall over all qrels) = regression number,
  tolerant to the single notch; (b) targeted behavioral invariants ("for 'Greek mythology' at
  least one Greek game in the top-5") = behavior unit tests.

Practical consequence: `questions.json` evolves from `{game_id, questions}` to **qrels**
`{query → {id: grade}}`, and the scorecard reports **Recall@K + nDCG@K** (besides MRR).

References: RAG/IR eval best practices (Qdrant; Towards Data Science on DCG/nDCG) and research
on LLM-as-judge / pooling (arXiv 2024–2025).

## 9. Harness design decisions

- **Small, frozen corpus, per SUITE.** ~50 games are enough to create noise/distractors and
  stay manageable (full labeling feasible). Instead of a single corpus that grows (and gets
  fragile), we organize **multiple suites**: each "class of problems" has its own stable suite
  (corpus + labels + queries). Adding cases = **a new suite**, not destabilizing the existing
  one.
- **Untagged = irrelevant** (accepted): with a small, frozen corpus the labeling stays
  complete → a manageable simplification.
- **Primary signal: inversions.** "No irrelevant above a relevant" already tells whether the
  data exists and is extracted sensibly. Recall@K and Precision@K accompany it.
- **Three DISTINCT enrichments (don't conflate them):**
  1. *Production enricher* (`GameEnricher`): improves what the SYSTEM embeds → goes to the
     embedder, measured by the harness.
  2. *Test oracle*: deep characterization of the test games (even with powerful models +
     online search). It is the **answer key**: it judges relevance and helps analyze failures.
     ⚠️ **NEVER fed to the system/LLM** → no *data leakage* (otherwise you'd test on training
     data).
  3. *test_tags* (`labels.json`): the structured part of the oracle, used to compute relevance.
     Bootstrapped from the catalog tags (already hand-curated), then refined. A file separate
     from the corpus.

### Suite structure

```
tests/fixtures/suites/<name>/
├── games.json     # frozen corpus (~50 real DTOs)
├── labels.json    # structured oracle: { "id": ["tag", ...] }  (bootstrapped from catalog tags)
└── queries.json   # [ { "query": "...", "tags": ["Mitologia"] } ]  query → aspect(s)
```

`relevant(query) = { game ∈ suite : query.tags ⊆ labels[game] }`.
Per-suite scorecard: **Recall@K, Precision@K, inversions** (+ MRR).
