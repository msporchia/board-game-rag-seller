# 🎬 A real session, on the real index — one take, unedited

> The other chat walkthroughs run on the frozen 50-game eval corpus. This one is different:
> **a live session against the full 501-game index**, exactly as a storefront would drive it —
> `POST /chat`, stateful `session_id`, `engine=agent` (qwen2.5:7b driving `search_catalog`
> itself), bge-m3 embeddings, the SEL-145 cooperative policy under the hard filter.
>
> **One take, recorded 2026-07-03, not edited and not retried.** Three turns land exactly the
> right games; one turn whiffs — and the whiff stays on the page, with its ticket. That is the
> deal this repo makes everywhere: measured beats curated.

---

**🧑 T1 — «ciao! cerco un gioco da regalare a una coppia di amici: giocano spesso in due la
sera dopo cena»**

| 🃏 | giocatori | durata |
|---|---|---|
| **Klask** — gioco di abilità per 2 | 2 | 10 min |
| **Patchwork** — strategico per 2, Uwe Rosenberg | 2 | 25 min |

> 🤖 «Ho pensato a dei giochi che potrebbero piacere a voi due di giocare insieme la sera!
> Klask è un gioco veloce e competitivo dove dovete affrontarvi in abilità! […] Patchwork è un
> gioco strategico che vi farà costruire insieme una bellissima tessera a puzzle.»

Two on-point picks for a couple's after-dinner slot, first try: the agent searched the live
catalog itself and both hits are genuinely 2-player games.

---

**🧑 T2 — «sì, gli piace la strategia ma niente partite infinite, direi massimo un'ora»**

| 🃏 | giocatori | durata |
|---|---|---|
| **Onitama** — strategico di arti marziali | 2 | 10 min |
| **Queendomino** — strategico per famiglie | 2-4 | 25 min |

> 🤖 «Onitama è un gioco di arti marziali con regole semplici ma strategie profonde. […]»

The constraint («strategy, under an hour») reshaped the search — both hits fit. One prose slip
kept honest: the pitch calls Queendomino «lavorare insieme» although its card says
`coop=False` — the grounding rules bind *which games* may be named, not every adjective; pitch
wording on the local 7B is a known, documented limit.

---

**🧑 T3 — «ah, dimenticavo: adorano i giochi cooperativi, dove si vince o si perde insieme.
c'è qualcosa di cooperativo che funzioni bene in due?» — ❌ the whiff, kept on the page**

> 🤖 «Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a
> dirmi qualcosa in più […]»

**This no-match is wrong** — the catalog does stock cooperative games that play well in two
(Magic Maze 1-8, Pandemic: La Caduta di Roma 1-5…), and turn 4 proves the coop axis works. The
agent's *search* whiffed, not the data: the anti-invention guarantee held (no title was made
up to fill the silence — that part is enforced in code), but an honest no-match spent on a
search bug is trust wasted. Tracked as
[SEL-147](../tickets/SEL-147-agent-false-nomatch-coop-two.md), which also names the
observability gap that makes it annoying to diagnose (tool-call args are not traced yet).

---

**🧑 T4 — «perfetto! e se invece volessi qualcosa di cooperativo per quando invitano altri
amici, tipo in cinque?»**

| 🃏 | giocatori | durata | `cooperative` |
|---|---|---|---|
| **Magic Maze** — società cooperativo | 1-8 | 15 min | ✅ True |
| **Pandemic: La Caduta di Roma** — cooperativo | 1-5 | 60 min | ✅ True |
| **Unlock! Heroic Adventures** — carte cooperativo | 1-6 | 60 min | ✅ True |

> 🤖 «Magic Maze è un gioco di avventura cooperativa dove dovete lavorare insieme per uscire
> da un labirinto prima che il negozio chiuda! […] Pandemic: La Caduta di Roma è un gioco
> strategico cooperativo dove dovete lavorare insieme per salvare la città […]»

The payoff turn. Three hits, **all three genuinely cooperative** — that `✅ True` column is the
curated hard filter of [SEL-145](../tickets/resolved/SEL-145-coop-infer-low-precision.md)
working on honest data (in June this exact request surfaced competitive games; the whole
chronology is in [`docs/experiments.md`](../experiments.md)). And the pitches are grounded in
the real games: «prima che il negozio chiuda» *is* Magic Maze's actual premise.

---

## What this take demonstrates — and what it doesn't

- **Demonstrated:** the agent searches the real catalog by itself and the latest message
  reshapes the search; the cooperative axis works end-to-end through the structured filter;
  the anti-hallucination floor holds even when a search fails.
- **Not demonstrated (known limits, tracked):** T3's search assembly
  ([SEL-147](../tickets/SEL-147-agent-false-nomatch-coop-two.md)) and pitch wording on the
  local 7B (the standing "stronger model" question the
  [simulation harness](../../tests/eval/ChatConversation/simulation/) exists to answer).

*Raw capture: every turn above is verbatim from the recorded session JSON (message, hits,
reply). Nothing was re-rolled.*
