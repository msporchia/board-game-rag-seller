# 💬 Chat — what the seller actually produced

> The [pipeline walkthroughs](README.md) show what enrichment does to *one game*. This one shows
> what the conversational layer does to *one customer* — and it does it on **real recorded
> sessions**, not a hand-written script. Every turn below is lifted verbatim from a
> [`ChatConversation`](../../tests/eval/ChatConversation) eval run: the message the customer sent,
> the query the seller assembled, the games the real retriever returned, and the reply it wrote.
> Nothing here is piloted for the demo — if it converges, it converged; if it whiffs, the whiff
> is on the page.

These transcripts come off a **frozen 50-game corpus** on a **local 7-8B model** (`llama3.1` for
the pipeline arm, `qwen2.5:7b` for the agent arm) — small models, on purpose. The stance is *if it
works on the 8B it flies on a stronger one* — and it is now **measured, not asserted**: the same
15 cases with Claude Sonnet 5 answering every LLM role (via the file-exchange responder harness,
same engine and oracle) score **15/15** vs the 8B's 0.733
([`experiments.md`](../experiments.md) row 14). The point of measuring on the weak model is to
see where it breaks, not to flatter it. Numbers are session-stamped and regenerate with every run —
the latest live in [`tests/eval/RESULTS.md`](../../tests/eval/RESULTS.md) and the full agent bundle
in [`REVIEW.md`](../../tests/eval/ChatConversation/REVIEW.md).

---

## Three engines, one contract

This is an R&D repo, so the conversational layer isn't *one* design — it's **three interchangeable
engines behind the same `reply(...)` contract**, measured on the same bench so they compare as
Δquality next to Δcost:

| Engine | Who decides the search | LLM's job | case pass | tok / chat | Cost stance — who it's for |
|--------|------------------------|-----------|:---------:|:----------:|----------------------------|
| **pipeline** | deterministic code (router picks strategy, filters, k) | only the sales pitch | **0.70** | 5 699 · ~1.95 calls/turn | **cheapest.** Thin margins, high volume — spend the least per conversation and accept the lower hit rate. |
| **piloted** | code loop; the model reformulates the query into *catalog language* | reformulate + pitch | **0.80** | ↓ 18% vs pipeline | **best quality-per-token.** More conversions *and* fewer tokens — the default if you have to pick one. |
| **agent** | the model itself, driving a `search_catalog` tool | search *and* pitch | **0.867** | 6 225 · ~2.59 calls/turn | **priciest per chat.** High-value carts where one extra won sale easily pays for the extra tokens. |

There is no single winner, and that's the point: the **agent** converts the most but costs the most
per conversation; the **pipeline** is the floor you can afford at volume; the **piloted** loop is the
sweet spot. Which one a storefront runs is an **economic decision** — *how many tokens is it worth
burning to land one more sale?* — and the answer differs for a €15 party game and a €90 collector
box. Same contract, swap the engine by `CHAT_ENGINE`; the rest of the stack doesn't move. The
interesting result isn't the leaderboard — it's *why* the order comes out this way, visible turn by
turn below, where the walkthroughs put the **two extremes side by side** (deterministic pipeline vs
tool-driving agent) on the same customer and messages, with the piloted loop as the measured middle.

---

## ① Quick match — the decided customer (both engines agree)

A customer who already knows what they want shouldn't be dragged through a guided questionnaire.
A precise title + purchase intent must route **straight to a proposal**.

> **Case `carcassonne-cliente-deciso`** — accepted: `34` Carcassonne by turn 1.

**🧑 «avete Carcassonne? vorrei comprarlo, è per stasera»**

| turn 1 | **pipeline** (llama3.1) | **agent** (qwen2.5:7b) |
|--------|-------------------------|------------------------|
| route | `QUICK_MATCH` *(decided customer → no GUIDED loop)* | model searches immediately |
| 🔎 query | *(code-assembled)* | «gioco da tavolo, tema città e campagna, meccaniche costruzione strade» · filters `players=2, duration≤180` |
| 🃏 table | **Carcassonne**, Orbis | **Carcassonne**, Solenia |
| result | ✅ converged turn 1 · 2 calls / 2 404 tok | ✅ converged turn 1 · 3 calls / 3 287 tok |

Both land Carcassonne in one turn. On the easy case the cheaper engine wins on cost and ties on
quality — which is exactly why the pipeline still exists alongside the agent.

---

## ② Vague → specific — where the engines diverge 🎯

This is the case that justifies the whole experiment. The customer narrows over three turns:
*expert group* → *sci-fi* → *"build a card-and-resource engine to make a planet habitable"*. By
turn 3 they have described **Terraforming Mars** in everything but name. Does the seller get there?

> **Case `terraforming-convergenza-vaga`** — accepted: `21` Terraforming Mars by turn 3.
> Confounders in-corpus: Progetto Gaia, First Martians, Mercanti di Venere.

### pipeline (llama3.1) — ❌ never converges

```
1. 🧑 «…siamo giocatori esperti e ci piacciono i titoli impegnativi»
   [GUIDED] → Specie Dominanti, La Festa per Odino
2. 🧑 «il tema che ci attira di più è la fantascienza»
   [GUIDED] → Specie Dominanti, La Festa per Odino
3. 🧑 «…costruisci un motore di carte e risorse per rendere abitabile un pianeta»
   [GUIDED] → Specie Dominanti, La Festa per Odino
```
**FAIL** · 6 calls / 8 433 tok. The deterministic router reads "undecided" and stays in `GUIDED`
for all three turns; the weak 8B only writes the pitch, so it re-proposes the **same two games**
even after the customer spells out the exact mechanic. Nothing in the design lets the *text the
customer just typed* reshape the search — the router already decided. The system is coherent and
grounded the whole way; it just never finds the right game.

### agent (qwen2.5:7b) — ✅ converges at turn 3

```
1. 🧑 «…siamo giocatori esperti e ci piacciono i titoli impegnativi»
   🔎 «gioco per adulti, meccaniche complesse, esperienza di gioco intensa»
   🃏 8Bit Box, Talisman: Il Cataclisma
2. 🧑 «il tema che ci attira di più è la fantascienza»
   🃏 (none) — 🤖 honest no-match: «al momento non ho in catalogo un gioco che
      corrisponde bene… dimmi qualcosa in più»
3. 🧑 «…costruisci un motore di carte e risorse per rendere abitabile un pianeta»
   🔎 «costruzione, meccanica carta, avventura spaziale»
   🃏 Terraforming Mars, Newton ✅
```
**PASS** · 7 calls / 8 292 tok. Note turn 2 is *worse* than the pipeline — the agent's own query
was weak and it honestly returned nothing rather than invent. But at turn 3 it **rewrites its own
search** from the customer's words and lands Terraforming Mars. The agent isn't better at every
turn; it's better at the thing that matters — letting the latest message move the search.

> **The lesson, measured:** at roughly the *same token cost* (8.3k vs 8.4k), giving the model
> control of the search converts a hard convergence the deterministic router can't. That single
> contrast is the argument for the agent arm — and the honest reason the pipeline still loses cases
> a stronger pitch model wouldn't save.

---

## ③ Honest no-match → recovery (anti-hallucination, enforced in code)

The seller may **never** invent a title to fill a silence. When the constraints exclude the whole
catalog, it must say so — and recover when they loosen.

> **Case `infeasibile-recupero`** — `players=2 + duration≤5` excludes all 50 games (shortest is
> 10 min). The honest no-match must fire with **zero** invented games; relaxing to 30 min must
> bring games back.

**Turn 1 — 🧑 «…abbiamo solo cinque minuti liberi»** · clicks `[per 2 giocatori] [max 5 minuti]`
- 🔎 filters `duration≤5` → **0 hits**
- 🤖 *«Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi…»* — no cards, no invention.

**Turn 2 — 🧑 «ok, in realtà possiamo arrivare a mezz'ora»** · click `[max 30 minuti]`
- 🔎 filters `duration≤30` → 5 hits
- 🃏 **Onitama, Tao Long** — games reappear; the relaxed click won, latest-wins.

Both engines behave identically here, because this isn't a model decision: the empty-result
short-circuit and the grounding rule are **enforced in code**, not trusted to the prompt. The
model can't talk its way past an empty retrieval.

---

## ④ The failure we kept on the page 🐛

A showcase that only shows wins is a brochure. This case is **red in the latest agent run** and
stays documented (and pinned by the eval) until it's fixed.

> **Case `contrordine-giocatori`** — **FAIL**. Constraint *reversal*: a turn-2 click must
> **replace** the players filter (latest wins), not pile onto it.

**Turn 1 — 🧑 «…gioco collaborativo con i miei figli di 8 anni»** · click `[per 4 giocatori]`
- 🔎 filters `players=2, age≤8` → 🃏 Fairy Tile, Fantascatti Special

**Turn 2 — 🧑 «anzi… meglio qualcosa che funzioni bene in due»** · click `[per 2 giocatori]`
- 🃏 **(none)** — 🤖 honest no-match.

What went wrong: by turn 2 the family-coop intent + the `players=2` correction should have surfaced
the two **Pandemic** titles (age 8, cooperative, 2-player). Instead the turn collapsed to an empty
no-match. The bug is in *combining* the reversed constraint across turns, not in grounding — the
seller correctly refused to invent, it just searched itself into a corner. It's a named
[`ChatConversation`](../../tests/eval/ChatConversation) case with an explicit oracle, so it scores
**red until the constraint-merge is fixed** — the failure is captured by the eval, not papered over.
The honest failure is part of the showcase on purpose — see also the
[Viticulture regression](viticulture.md) on the pipeline side.

---

## The five beats, made concrete

The walkthroughs above are the same five beats the [pipeline showcase](README.md) uses, applied to
a conversation instead of a single game:

1. **The opening turn** — the raw message, and (pipeline arm) the strategy the deterministic router
   picks: `GUIDED` / `EXPLANATORY` / `DISCOVERY` / `QUICK_MATCH`. ① shows `QUICK_MATCH` firing on a
   decided customer; ② shows `GUIDED` getting *stuck*.
2. **Retrieval** — the query and filters assembled from the turn, and the real hits. ② is the whole
   story: same customer, two different searches, two different outcomes.
3. **The grounded pitch** — the `{intro, recommendations, quick_replies}` reply, with only the ids
   that survived grounding validation. Every 🃏 above is a game that was really retrieved.
4. **The follow-up turn** — a quick-reply click parsed into real `SearchFilters`. ③ and ④ both turn
   on a click becoming a hard filter; ④ is where merging that click across turns breaks.
5. **Enforced vs generated** — ③ is the line in the sand: the honest no-match and the
   anti-hallucination drop are **guaranteed by code**; the warm Italian prose is **produced by the
   model** (and therefore measured, not trusted).

→ Design and findings: [`docs/chat.md`](../chat.md) · the three engines: [`docs/idee.md` §Q](../idee.md) ·
back to the [pipeline walkthroughs](README.md).
