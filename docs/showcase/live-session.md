# 🎬 Live sessions — the real seller, on the real index

> Unedited sessions against the full 501-game index, recorded in-process by
> [`tests/record_live_session.py`](../../tests/record_live_session.py) — which captures what an
> HTTP transcript cannot: **the searches the agent actually ran**. Nothing below is piloted,
> re-rolled or edited — each session is one take, flaws included, each flaw with its ticket.
>
> Two tiers, same engine, same catalog, same customer scripts:
> - **Local tier** — `qwen2.5:7b` at the wheel: free, on-device, shippable today. It works;
>   it is not particularly fluent, and its flaws are annotated below.
> - **[Frontier tier](#the-frontier-tier--same-engine-same-catalog-a-top-model-at-the-wheel)**
>   — **Claude Sonnet 5** at the wheel (via the file-exchange responder harness): *this is how
>   the same engine sells with a top model.* The model swap is one seam — that is the point of
>   the provider-swappable design.

**How to read a turn** — every turn shows the full chain:

- 🧑 the customer's message (Italian by design — real catalog, real language; *English gloss
  in italics*);
- 🔎 **the search the model actually composed**: free-text query + structured filters + hit
  count. This is the real "prompt under the hood". A `forced` badge means the model went
  silent and the **code** ran the safety-net search with the customer's own words
  ([SEL-147](../tickets/resolved/SEL-147-agent-false-nomatch-coop-two.md));
- 🃏 the cards that survived grounding — only games really retrieved may be named;
- 🤖 the reply the seller wrote (trimmed; *English gloss in italics*).

---

## ① `coppia-serale` — vague opener → constraints → the cooperative ask

**🧑 T1** «ciao! cerco un gioco da regalare a una coppia di amici: giocano spesso in due la sera dopo cena»
*(hi! looking for a gift for a couple of friends: they often play in two, evenings after dinner)*
- 🔎 «gioco da tavolo per due persone, giochi serali, non troppo c…» · `players=[2]` → 5 hit
- 🃏 **Patchwork** (2 · 25 min) · **Obscurio** (coop)
- 🤖 «Sono felice di aiutarti a trovare un gioco da tavolo perfetto per la tua coppia di amici…»

**🧑 T2** «sì, gli piace la strategia ma niente partite infinite, direi massimo un'ora»
*(they like strategy but no endless games — an hour tops)*
- 🔎 «gioco strategico per 2 persone» · `players=[2], duration≤60` → 5 hit
- 🃏 **Patchwork** · **Offboard** · **Onitama** (2 · 10 min)

The new constraint became a **structured filter** (`duration≤60`), not just words in a query.

**🧑 T3** «ah, dimenticavo: adorano i giochi cooperativi, dove si vince o si perde insieme. c'è qualcosa di cooperativo che funzioni bene in due?»
*(oh, I forgot: they love co-op games, where you win or lose together. anything cooperative that works well in two?)*
- 🔎 `forced` «ah, dimenticavo: adorano i giochi cooperativi…» → 5 hit
- 🃏 **Nome in Codice: Duetto** (2 · 25 min · coop ✅) · **Pandemic: Reazione Rapida** (2-4 · 20 min · coop ✅)
- 🤖 «Ti servono giochi cooperativi per due giocatori. […] **Nome in Codice - Duetto** è un gioco di deduzione cooperativa dove dovete lavorare insieme…» *(you need co-op games for two players — Codenames Duet is a cooperative deduction game where you work together…)*

**The model went silent here** (no tool call — the very failure that produced a *false* «non ho
in catalogo» in the first recorded take): the SEL-147 floor searched with the customer's own
words and came back with the two best co-op-for-two answers the catalog has. The honest
no-match now has to be *earned* by an empty search, never granted to the model's silence.

**🧑 T4** «perfetto! e se invece volessi qualcosa di cooperativo per quando invitano altri amici, tipo in cinque?»
*(perfect! and something cooperative for when they invite friends over — five of them, say?)*
- 🔎 `forced` «perfetto! e se invece volessi qualcosa di cooperativo per qu…» → 5 hit
- 🃏 **Unlock! Timeless Adventures** (1-6 · coop ✅) · **Dungeon Time** (1-5 · coop ✅)

---

## ② `cliente-deciso` — the weak take, kept on purpose

**🧑 T1** «buongiorno, avete Carcassonne? vorrei regalarlo a mia sorella, mi serve per stasera»
*(good morning, do you have Carcassonne? I'd like it as a gift for my sister, I need it tonight)*
- 🔎 «gioco da tavolo per 2-5 persone, meccanica di tessera, tema …» · `players=[2]` → 5 hit
- 🃏 Terra Mystica · Descent — **Carcassonne is not on the table** ❌

**The customer named a title; the model searched a paraphrase.** Carcassonne is in stock (it
ranks #1 for this in the eval bench most runs — this take missed it): exact-title lookup is a
retrieval axis semantic search doesn't guarantee, a known lever for the agent tier (SEL-113).

**🧑 T2** «perfetto! e c'è qualcosa di simile da affiancare al regalo, sempre di piazzamento tessere ma un po' più moderno?»
*(and something similar to go with the gift — still tile placement, a bit more modern?)*
- 🔎 «gioco piazza tessere cooperativo» · `players=[2]`, **`cooperative=True`** → 5 hit
- 🃏 Magic Maze · TIME Stories ×2 (all coop ✅ — but nobody asked for coop)

**The model invented a filter**: `cooperative=True` was never requested. The search line makes
the fabrication visible — which is exactly why the searches are on the page — and it's the
family of [SEL-143](../tickets/SEL-143-cooperative-fabricated-from-unknown-reference.md)
(anti-invented-filters, an open backlog lever). A weaker session than the others; it stays.

---

## ③ `regalo-bambino` — constraints accumulate, the floor carries the tail

**🧑 T1** «cerco un regalo per il compleanno di mio figlio, compie 8 anni»
*(a birthday gift for my son, he's turning 8)*
- 🔎 «gioco per bambini, età minima 8 anni» · `age≤8` → 5 hit
- 🃏 **Fairy Tile** · **NasconDino**

**🧑 T2** «bello! gioca spesso con la sorella più piccola, meglio qualcosa che possano fare insieme senza litigare»
*(he often plays with his younger sister — better something they can play together without fighting)*
- 🔎 `forced` → 5 hit · 🃏 **Unlock! Secret Adventures** · **CuBirds** · **Coloretto**

**🧑 T3** «l'ideale sarebbe una cosa da mezz'oretta, non di più»
*(ideally about half an hour, no longer)*
- 🔎 `forced` «l'ideale sarebbe una cosa da mezz'oretta, non di più» → 5 hit
- 🃏 **Otto Minuti per un Impero** (2-5 · **15 min**) · **Fantascatti: 5 Minuti a Mezzanotte** (2-8 · **20 min**)

Even through the safety net, the semantic layer carries the constraint: «mezz'oretta» surfaced
15-20 minute games without any structured duration filter.

---

## ④ `esperti-fantascienza` — the June convergence case, live

The eval bench has a famous case: a customer describes Terraforming Mars in everything but
name, and only the agent engine converges ([chat walkthrough](chat.md)). Here it happens **on
the live index**, unscripted.

**🧑 T1** «siamo un gruppo di giocatori esperti e cerchiamo un titolo impegnativo per le nostre serate»
*(we're a group of expert players looking for a demanding title)*
- 🔎 «gioco da tavolo impegnativo per giocatori esperti» · `players=[4], cooperative=False` → 5 hit
- 🃏 Disney Villainous · Talisman: Il Cataclisma · Jamaica

**🧑 T2** «il tema che ci attira di più è la fantascienza, meglio se gestionale»
*(the theme we like most is sci-fi, ideally a management game)*
- 🔎 «gioco fantascienza gestione» → 5 hit
- 🃏 **Magnastorm** · Terraforming Mars: Turmoil *(the expansion — close, not there yet)*

**🧑 T3** «ci piacciono i giochi dove costruisci un motore di carte e risorse, tipo rendere abitabile un pianeta»
*(we like games where you build an engine of cards and resources — like making a planet habitable)*
- 🔎 `forced` «ci piacciono i giochi dove costruisci un motore di carte e r…» → 5 hit
- 🃏 **Terraforming Mars** (1-5 · 120 min) — **#1 out of 501** 🚀
- 🤖 «Fantascienza, gestione e costruzione! […] **Terraforming Mars** è un gioco strategico dove dovete […] trasformare il pianeta Marte in un nuovo mondo abitabile.» *(sci-fi, management and building! Terraforming Mars — transform planet Mars into a habitable new world.)*

The customer never says the name; the third message *describes* the game, and the search —
the customer's own words, verbatim — puts the right box first out of 501. One pitch slip kept
honest: «dovete lavorare insieme» (TM is competitive; wording on the local 7B remains the
documented limit the
[simulation harness](../../tests/eval/ChatConversation/simulation/run.py) exists to measure).

---

## The frontier tier — same engine, same catalog, a top model at the wheel

The two sessions below are the SAME customer scripts, the SAME live 501-game index, the SAME
`AgenticChat` engine — the only change is who answers the LLM prompts: **Claude Sonnet 5**,
through the file-exchange responder harness (`--exchange`; the transport is a file exchange
rather than an API call — the API integration is SEL-110). Every weakness annotated in the
local takes disappears on its own, with no code change:

### ①-bis `coppia-serale` — frontier take

**🧑 T3** «…adorano i giochi cooperativi, dove si vince o si perde insieme. c'è qualcosa di cooperativo che funzioni bene in due?»
- 🔎 «gioco cooperativo, si vince o si perde tutti insieme contro il g…» · `players=[2], duration≤60, cooperative=True` → 5 hit
- 🃏 **Pandemic: La Caduta di Roma** (1-5 · 60′ · coop ✅) · **Unlock! Heroic Adventures** (coop ✅) · **Yokai** (2-4 · 20′ · coop ✅)
- 🤖 «Ottima notizia: il cooperativo funziona benissimo anche in due […] **Pandemic: La Caduta di Roma** li mette fianco a fianco a difendere l'impero da invasioni e crisi […] È il classico *"o vinciamo o perdiamo insieme"* che stavano cercando. […] **Yokai** è più breve e leggero, circa 20 minuti […] un cooperativo veloce da rifare più volte in una serata.» *(co-op works beautifully in two — Pandemic: Fall of Rome puts them side by side defending the empire; Yokai is the quick one you replay all evening.)*

No silence, no safety net needed: the model composed the query AND all three structured
filters (`players`, `duration`, `cooperative`) from the conversation on its own — the turn the
local model needed the SEL-147 floor for.

**🧑 T4** «…e se invece volessi qualcosa di cooperativo per quando invitano altri amici, tipo in cinque?»
- 🔎 «gioco cooperativo per gruppo numeroso…» · `players=[5], cooperative=True` → 5 hit
- 🃏 **Magic Maze** · **Massive Darkness** · **Pandemic: La Caduta di Roma** (tutti coop ✅)
- 🤖 «**Magic Maze** è perfetto per cinque: si esplora un centro commerciale in tempo reale muovendo tutti gli eroi insieme, **ma senza parlare tra voi**, in appena 15 minuti di caos organizzato che fa ridere e sudare allo stesso tempo.» *(you all move the heroes together in real time — but you're not allowed to talk: 15 minutes of organised chaos.)*

That «senza parlare tra voi» is Magic Maze's *actual* signature rule — the pitch sells the
real game, not a generic blurb.

### ②-bis `cliente-deciso` — frontier take (the weak local session, redeemed)

**🧑 T1** «buongiorno, avete Carcassonne? vorrei regalarlo a mia sorella, mi serve per stasera»
- 🔎 **«Carcassonne»** · *(no filters)* → 5 hit
- 🃏 **Carcassonne — Nuova Edizione** (2-5 · 45′) · **Carcassonne: La Torre** (espansione)
- 🤖 «Ottima scelta per un regalo dell'ultimo minuto, ce l'abbiamo pronto in negozio! **Carcassonne** nella sua Nuova Edizione è esattamente quello che cercava […] perfetto da scartare stasera stessa. Se vuole arricchire il regalo, **Carcassonne: La Torre** è l'espansione ideale da abbinare.» *(great last-minute gift, we have it in store — and The Tower expansion pairs perfectly if you want to enrich the gift.)*

The local take searched a paraphrase and missed the named title; the frontier model simply
**searched the title verbatim** — and upsold the expansion. The invented `cooperative=True`
filter of the local T2 is gone too: the follow-up search is exactly what was asked
(«gioco moderno di piazzamento tessere…», no fabricated constraints → Azul: Summer Pavilion,
Bärenpark, Fairy Tile).

*(The other two archetypes' frontier takes are recorded the same way —
`python -m tests.record_live_session --exchange … --suffix=-frontier`.)*

---

## What the takes demonstrate — and what they don't

- **Demonstrated (local tier):** real searches on the real catalog, visible per turn (query +
  structured filters + hits); constraints becoming filters; the cooperative axis working
  through curated data; the SEL-147 floor turning model silence into grounded proposals; a
  described-not-named game found first out of 501 — free, on-device.
- **Kept honest (local tier):** a named title missed (② T1), an invented filter caught *by the
  search log itself* (② T2), pitch wording slips on the 7B — each mapped to its ticket or
  backlog lever, none edited out.
- **Demonstrated (frontier tier):** every one of those flaws disappears with the model swap
  alone — title searched verbatim, no invented constraints, all three coop filters composed
  unprompted, pitches grounded in each game's real signature details. Consistent with the eval
  bench, where the same swap scores **15/15** ([ledger](../experiments.md) rows 14 and 16).
  The local 7B is the bottleneck; the engine is the product.

*Regenerate the raw sessions anytime:
`docker compose exec seller-api python -m tests.record_live_session --all`
(JSON per session in `data/live-sessions/`, gitignored).*
