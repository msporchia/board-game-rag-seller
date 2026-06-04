# Step 2 — Web

**Status:** ✅ implemented · **Code:** `app/ingestion/enricher/web.py`

## Why this step exists

After the Curator (step 1), some games still have **genuine gaps** — facts that are missing
from *every* internal source: not in the structured fields, not in the main description, not in
any of the secondary source descriptions. For those, the data simply isn't in our catalog.

The Web step is the **fallback**: go online to recover the missing facts from public sources
(mostly reviews) — but with two hard rules. **Only for what's actually missing** ("online only
once the local sources are exhausted"), and **never trust the web blindly**: the open web is
full of wrong, thin, or off-topic pages (a retailer listing, a homonym game, a confident
Wikipedia mismatch). So this step is built as a *verified* fetch, not a free-text grab — it
exists to **complete the dataset from outside without polluting it**.

## What it does

A small retrieve-and-verify pipeline. It activates only if the game has `missing_info`:

1. **Clean the name** — strip the marketing tail (`"Viticulture Essential - Gioco da
   Tavolo…"` → `"Viticulture Essential"`) so the search query is sharp.
2. **Search** the web (DuckDuckGo by default, swappable).
3. **Rank the sources** (deterministic): drop the blocklist (retailers, our own shop), put the
   whitelist of trusted board-game sites first, leave unknown domains at the tail.
4. **Fetch** the top pages with a browser User-Agent (some good sources block bare bots),
   cached so we never re-download.
5. **Judge** each page with the LLM: *is this really about this game* (not a homonym)? *is it a
   serious source* (a review/entry, not a bare product listing)?
6. **Extract** the missing facts with the LLM — each backed by a **verbatim quote** from the
   page.
7. **Validate** the quote is really in the page text; keep only what passes (same
   anti-hallucination rule as the Curator).
8. **Apply** the verified facts to the description **with provenance** (which source said what),
   and remove them from `missing_info`.

The whitelist (priority) + LLM judgment on unknown domains is what makes it *hybrid*: we say
**where to look** rather than letting a small model roam — with an 8B, letting it pick sources
freely is unreliable.

## How we expect it to behave

- **Fallback only.** It runs for real gaps, never as the default path. If nothing is missing,
  it does nothing.
- **Never invents.** A fact is kept only if the LLM quoted it *and* the quote is verified in the
  source text. No quote → discarded → the gap stays open.
- **Trust the good, judge the unknown, drop the bad.** Known-good sites rank first; unknown ones
  must pass the LLM's relevance + seriousness gate; retailers and our own shop are dropped.
- **Target reviews.** For board games, reviews are abundant and richer than publisher pages.
- **Be careful with numbers.** Descriptive facts (setting, theme) agree across sources and are
  safe; numeric ones (duration, age) **diverge** between sources — so they need cross-checking
  or should defer to certain data.
- **Keep provenance.** Every extracted fact records its source, building a picture of which
  sources are reliable over time.

## How we measure it

The hard problem: the live web is **non-deterministic** — search results and page contents
change daily, so a test that hit the network would break on every run and measure the web, not
our code. The fix is **record / replay**: the recorder freezes, once, the real search results
and the fetched pages into a fixture; the eval then replays the step over that frozen input, so
the **only variable left is the LLM**.

On top of that, the step is measured **one phase at a time** — because each phase has a distinct
job and a distinct failure mode, and an end-to-end pass/fail wouldn't tell you *which* one
broke:

| Phase | LLM? | What the oracle checks |
|-------|------|------------------------|
| **Ranking** | no | the right domains are on top, in order (`top_domains`); the bad ones never appear (`must_drop_domains`). If ranking is wrong, the LLM sees the wrong pages. |
| **Judgment** | yes | per page: `is_this_game` / `is_serious` match the oracle — the gate that avoids extracting from wrong or thin pages. |
| **Extraction** | yes | per fact: it's extracted, the value contains the expected gist, and the quote is verbatim in the page. |

The oracle (the `expect` block in each fixture) is **partial by design** — we assert only what
we're sure of. Change the model and only the LLM phases move; the diff tells you exactly on
which URL/info. The ranking phase needs no LLM, so it runs even offline.

## Example: before → after

Real game — **Viticulture**, arriving from the Curator with
`missing_info = [ambientazione, durata, numero giocatori]`.

**Before:** the catalog description never states *where* the game is set; the setting slot is an
open gap.

**The step, phase by phase:**
- *Ranking* — the query returns our own shop page (`gamenest.example`), three `goblins.net`
  entries, and some unknown blogs. Ranking drops our shop (blocklist), puts the three trusted
  `goblins.net` pages on top, unknowns at the tail.
- *Judgment* — the `goblins.net` review pages pass the gate (`is_this_game` ✓, `is_serious` ✓).
  The gate is *meant* to also reject non-reviews — e.g. the bare *Collector's Edition* box
  description (`is_serious` should be ✗) — and games-with-the-same-name; those rejections are
  the gate's current weak spots (see Potential improvements).
- *Extraction* — from the review text *"…rustic, pre-modern **Tuscany**…"* the LLM extracts
  **ambientazione = "Toscana"**, and the quote is verified verbatim in the page. (Descriptive
  facts like this extract reliably; numeric ones — duration, player count — are where extraction
  currently struggles.)

**After:** the description gets a provenance line —
`ambientazione: Toscana (fonte: goblins.net)` — and `ambientazione` is removed from
`missing_info`. A real gap, filled from a trusted source, with evidence. (The numeric gaps —
duration, players — are the riskier ones and only get filled if a source states them explicitly.)

## Potential improvements

Each measurable on the same per-phase replay harness (swap the variable, re-run, read the diff):

> Where the eval currently fails (the natural to-do list): the per-phase replay run is **green
> on ranking and on descriptive extraction**, but red on two clusters — **numeric extraction**
> (`durata`, `numero giocatori`) and the **judgment gate** (homonyms and non-review pages). The
> improvements below target exactly those.

### 1. Harden the judgment gate (the safety-critical one)

This is the most important, because a page that passes the gate wrongly **poisons everything
downstream**. The eval shows two leaks:
- **Homonyms** — a different game with the same name is accepted (`is_this_game` should be
  *false*): e.g. *Daybreak* matched against *One Night Ultimate Werewolf: Daybreak*,
  *Spirit Island* against *Malagasy*.
- **Non-reviews** — a bare box/product page is accepted as serious (`is_serious` should be
  *false*): e.g. a *Collector's Edition* box description, an e-commerce product page.

Leads: a stricter prompt (require the page to state the game's *own* identifying facts before
trusting it), a name/title cross-check before the LLM, or a stronger model on this gate. All
measurable directly on the judgment phase.

### 2. Cross-verify numeric facts

Numeric facts are the other failure cluster. They're hard two ways: the model often fails to
extract a clean numeric value at all, and across sources they **diverge** — one review says
45 min, another 90. Today the step also takes the **first** source's value (whitelist-first),
which is fragile. Better: require **agreement across ≥ 2 sources** for numeric facts, or always
defer to certain data when present. Measurable by adding fixtures where sources disagree and
asserting the cross-checked value.

### 3. Try different models

As with the Curator, the judgment and extraction quality *is* the model's quality — and the two
gates here (relevance / seriousness) and the quoted extraction stress different model strengths
(instruction-following under "don't invent", reading comprehension). Swapping the model is a free
A/B on the replay harness: only the LLM phases move, the diff says where.

### 4. Cache extractions, not just fetches

The store currently caches the fetched **pages** (no re-download), but re-runs the **LLM** every
time. Persisting the verified extractions (fact + quote + provenance) would let a re-ingest skip
the LLM call entirely for already-seen pages — faster and cheaper, with the provenance already
recorded.

### 5. Grow the fixture corpus

The replay corpus is the ruler, and it's still small. The known hard cases to add: more
**homonyms**, **retail-heavy** queries (mostly shops), and **Wikipedia traps** (for a game it
doesn't cover, Italian Wikipedia returns a confident *wrong* match — e.g. Viticulture →
Carcassonne). These all stress the judgment gate (improvement 1), the part that protects
everything downstream.
