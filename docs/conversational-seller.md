# Part 2 — the conversational seller, in full 💬

> The summary and the turn diagram live in the [README](../README.md#part-2--the-conversational-seller-).
> This page is the full story: the trust invariants, the per-turn strategy, the policy system,
> the three engines and how they're measured — every claim with the class that enforces it and
> the test that proves it.
>
> ⚡ **Prefer to see it?** [Watch four unedited sessions on the live 501-game index in the
> interactive demo](https://msporchia.github.io/board-game-rag-seller/demo/) — every search the
> agent ran, on the page.

This is the salesperson the problem statement asked for. A customer who only knows *Monopoly*
won't browse a genre tree — so the seller doesn't show one. Each turn it **reads the message**,
decides **how to answer** (ask one clarifying question, explain a mechanic, or just propose), and
always lands on **real boxes on the shelf** — never an invented title. It's the
[Part 1 retrieval engine](retrieval-engine.md), wrapped in a conversation that does the asking.

Send a `session_id` and the turn carries memory across the conversation (SQLite checkpointer);
omit it and the same core runs as a single stateless pitch. The contract is the same either way:
`{message, games, quick_replies}`.

## Why you can trust what it says

Two invariants are enforced **in code, never trusted to the model**:

- **Anti-hallucination grounding** — a pitched game must be in the retrieved set; an invented id
  is dropped *and its sales pitch goes with it*. The customer message is **assembled in code**
  from the surviving recommendations, so the prose can only ever describe games that are on the
  cards. The first measured failure — text and cards naming different games — is now
  **structurally impossible**, not patched after the fact
  ([ADR-0002](adr/0002-grounding-enforced-in-code.md) · [`ChatAdvisor`](../app/chat/advisor.py) ·
  [tested](../tests/unit/ChatAdvisor/)).
- **Deterministic fallback** — if structured output fails, the turn degrades to an honest
  scripted reply over the retrieved games. No 500, no invented recommendation.

## Asking the right questions

The "right few questions" are a **strategy chosen per turn** from how the customer reads
([`TurnAnalyzer`](../app/chat/analyzer.py): enthusiasm, decisiveness, expertise — measured
per-dimension in [tests/eval/TurnAnalyzer](../tests/eval/TurnAnalyzer/)) — so a hesitant beginner
and a decided enthusiast get different conversations:

| Strategy | When | What the turn does |
|----------|------|--------------------|
| **GUIDED** | undecided / beginner | 1–2 clear options **+ one simple question** to narrow down |
| **EXPLANATORY** | curious beginner | explain the mechanics in plain words and analogies |
| **DISCOVERY** | enthusiast | free-form, propose creatively across the catalog |
| **QUICK_MATCH** | decided — or the chat is stalling | 3–4 concrete games, **now** |

Routing is deterministic — decided in code, not asked of a prompt — and **after 3 turns with no
concrete proposal the seller forces a QUICK_MATCH**, so a conversation never loops forever
without a buyable answer.

With every answer the seller also offers **tappable quick replies** — suggested refinements about
the *game*, like *"plays in under 30 minutes"*. Tapping one isn't small talk: it becomes a
**real search filter** on the game's own attributes
([`ClickParser`](../app/chat/choices/parser.py) + one [`Choice`](../app/chat/choices/choice.py)
class per attribute · [tested](../tests/unit/ClickParser/)), so every tap genuinely narrows the
catalog instead of being a decorative chip.

## Steering the seller — policies switched on by name

A storefront often needs to *bias* the seller — run a Christmas campaign, push a category — 
without handing the client a free prompt field to inject into. So the bias is a **list of named
policies** on the request (`custom_policy: ["christmas_sale", "promote_cooperative"]`); each name
resolves to a small class in a registry ([`PolicySet`](../app/chat/policies/policy_set.py) ·
[the library](../app/chat/policies/library/)), and an unknown name is ignored, never an error.

A policy isn't a fixed setting — it's **middleware wrapped around the turn's stages**, so it does
exactly as much as it needs: `promote_cooperative` puts itself *in the middle of the fetch*,
`christmas_sale` reshapes the *pitch* (gift framing, no invented prices), `force_quick_match`
overrides the routing. Adding a behavior is **one file and one registry line**. The boundary that
keeps it safe: a policy changes **behavior, not truth** — it can only reorder games that were
actually retrieved; no policy can override the grounding rule. Each policy is unit-tested on its
own ([PromoteCooperative](../tests/unit/PromoteCooperative/) ·
[ChristmasSale](../tests/unit/ChristmasSale/) ·
[ForceQuickMatch](../tests/unit/ForceQuickMatch/)). Design: [`idee.md`](idee.md).

## Three engines, one contract

Behind the same `reply(...)` contract sit interchangeable engines, switched by `CHAT_ENGINE` and
per-request for shadow runs ([ADR-0003](adr/0003-interchangeable-chat-engines.md)):

- **pipeline** — [`ChatGraph`](../app/chat/graph.py): the decomposed graph, every decision
  (route, filters, k) made in code, the weak 8B does only the pitch.
- **piloted** — [`PilotedChat`](../app/chat/piloted.py): a code-piloted loop where the model
  reformulates the search query into *catalog language* (it turns *"we all play together against
  the game"* into *"cooperative, win or lose as a team"* — the lexical gap the embedder can't
  bridge on its own); a zero-result turn triggers one **informed** retry or an honest no-match.
- **agent** — [`AgenticChat`](../app/chat/agentic.py): the model drives the
  [`search_catalog` tool](../app/chat/tools/search_catalog.py) itself, deciding when and with
  what words to search; the answer is still assembled in code over what the tool returned (same
  grounding). The pipeline's `llama3.1:8b` can't drive tools — as predicted — but `qwen2.5:7b`
  runs the loop end-to-end (~8-10s/turn), using the structured filters (`players=2`, not buried
  in the query text). Every tool call is recorded (`{query, filters, hits}`) so tool-use quality
  is measurable, the tool tolerates malformed args, and a silent turn is floored by a forced
  search with the customer's own words — an honest no-match must be *earned* by an empty search,
  never granted to silence
  ([SEL-147](tickets/resolved/SEL-147-agent-false-nomatch-coop-two.md) ·
  [test_forced_search](../tests/unit/AgenticChat/test_forced_search.py)).

[`TieredChat`](../app/chat/tiered.py) ([tested](../tests/unit/TieredChat/)) degrades a failed
primary turn to the pipeline so the customer always gets an answer; its sliding-window circuit
breaker is designed but not built yet (see [`idee.md`](idee.md)).

| engine | who drives the search | case pass | note |
|--------|-----------------------|:---------:|------|
| pipeline | deterministic code | 0.667 | re-baselined 2026-07-03 |
| piloted | code loop, model reformulates | 0.80 · −18% tok | June bench, re-run pending |
| agent · `qwen2.5:7b` | the model itself, via a tool | **0.733** | both cooperative cases pass |

Read the rates knowing what the bench is: **adversarial by design**. The 15 cases are the
nasty customers — constraint *reversals* mid-conversation, distractor traps, infeasible requests
that must produce an honest refusal (not a plausible invention), a forced-proposal deadline. An
engine could score high on easy customers and prove nothing; these rates are earned where it
hurts — and on the same nasty cases the measured ceiling is **15/15**. Case-pass is honestly
noisy run-to-run (the same 15 cases scored 0.60/0.80/0.87 on identical inputs) — single runs are
samples, not verdicts. And this isn't a leaderboard but a **quality/cost curve**: the agent converts the most but costs the most per chat, the pipeline is
the floor you can afford at volume. Which arm a storefront runs is an economic call, swapped by
`CHAT_ENGINE` behind one contract.

## Measured the same way as the pipeline

Real LLM, hand-written oracles, one suite per node, plus a whole-conversation suite that replays
scripted multi-turn sessions through the production engine — still rule-scored, never an
unreadable end-to-end blob:

| Suite | What it measures |
|-------|------------------|
| [TurnAnalyzer](../tests/eval/TurnAnalyzer) | reading the customer: per-dimension accuracy vs labeled turns |
| [ChatPitch](../tests/eval/ChatPitch) | how often the model delivers a *grounded* recommendation instead of the fallback, per strategy |
| [ChatRetrieve](../tests/eval/ChatRetrieve) | conversational query assembly: recall@k of the games the turn should surface |
| [ChatConversation](../tests/eval/ChatConversation) | full multi-turn sessions on the production engine, per arm: convergence, filter integrity across turns, the forced-proposal rule, fallback rate, plus LLM calls/tokens so arms compare as Δquality next to Δcost |

**Latest measured results: [`tests/eval/RESULTS.md`](../tests/eval/RESULTS.md)** — regenerated at
the end of every eval run. And for *"ok, but what did it actually produce?"*: the agent run is
exported as a human-readable [review bundle](../tests/eval/ChatConversation/REVIEW.md) — every
search the model ran, every reply it wrote, next to the goal and a rubric for what a pass rate
can't score (aptness, invented constraints, tone, giving up too early).

## What a session looks like

A **real** turn from the agent run (case `infeasibile-recupero`, lifted verbatim from the
[review bundle](../tests/eval/ChatConversation/REVIEW.md)):

> 🧑 *«in pausa pranzo io e un collega abbiamo solo cinque minuti liberi»* · click `[per 2 giocatori] [max 5 minuti]`
>
> 🤖 *«Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi…»*
> &nbsp;&nbsp;— `duration ≤ 5` matches **nothing in the catalog**, so the seller says so. No cards, no invented game.
>
> 🧑 *«ok, in realtà possiamo arrivare a mezz'ora»* · click `[max 30 minuti]`
>
> 🤖 *«**Onitama** è perfetto per voi: un duello veloce e strategico… in solo 10 minuti! **Tao
> Long** offre un gioco di strategia breve…»*
> &nbsp;&nbsp;— the click became a real `duration ≤ 30` filter; games reappear, both really in stock.

The same customer run through **two engines side by side** — including the convergence case the
deterministic pipeline can't crack — is in [`showcase/chat.md`](showcase/chat.md). And beyond the
eval bench: [**live sessions on the full 501-game index**](showcase/live-session.md) —
unedited takes, regenerable with one command, every flaw annotated with its ticket, and the
same sessions re-recorded with **Claude Sonnet 5** at the wheel (the frontier tier): the
model-bound flaws vanish with the swap alone.

## Known limits, tracked 🚧

Honest status — every open edge has a ticket or a red eval pinning it, none is hidden:

- **Pitch quality on the local 7-8B is the open bottleneck.** The *mechanics* hold end-to-end
  (grounding, memory, fallback, traces — no 500s), but the small model's sales copy is thin. The
  stance *"if it works on the 8B, it flies on a stronger model"* is measured, not rhetorical:
  the [file-exchange responder harness](../tests/eval/ChatConversation/simulation/) replays the
  same cases with a stronger model answering every LLM role under the same engine, retrieval
  and oracle — built so any stronger model can be benchmarked *before* being wired into
  production (the API integration is SEL-110). With **Claude Sonnet 5** as the responder, the
  agent arm goes **0.733 → 15/15** (all three non-convergences and the `min_games` miss
  disappear; zero turns without a tool call; details in [experiments.md](experiments.md),
  row 14).
- **A few cases are still red** — e.g. constraint *reversal* across turns, where a corrected
  click should *replace* the old filter, not pile on (click→filter merge isn't wired in the
  agent tier yet). *Why* the 7B stops driving tools with longer history remains a model-quality
  question (SEL-113).
- **The cooperative verdict policy is a declared stopgap** — True only from curated catalog
  signal, because the local model's inferred True failed a zero-wrong-verdict gate; the revisit
  is [SEL-146](tickets/SEL-146-cooperative-verdict-revisit.md).

## No claim without a class and a test

| The claim | The class that enforces it | The proof |
|---|---|---|
| "An invented id is dropped, and its pitch goes with it" | [`ChatAdvisor`](../app/chat/advisor.py) | [tests/unit/ChatAdvisor](../tests/unit/ChatAdvisor/) |
| "An honest no-match must be earned, never granted to silence" | [`AgenticChat`](../app/chat/agentic.py) | [test_forced_search](../tests/unit/AgenticChat/test_forced_search.py) |
| "A tap becomes a real search filter" | [`ClickParser`](../app/chat/choices/parser.py) + the [`Choice`](../app/chat/choices/choice.py) registry | [tests/unit/ClickParser](../tests/unit/ClickParser/) |
| "A policy changes behavior, not truth" | [`PolicySet`](../app/chat/policies/policy_set.py) · [library](../app/chat/policies/library/) | [PromoteCooperative](../tests/unit/PromoteCooperative/) · [ChristmasSale](../tests/unit/ChristmasSale/) |
| "Three engines, one contract — degrade, don't 500" | [`TieredChat`](../app/chat/tiered.py) over [`ChatGraph`](../app/chat/graph.py) · [`PilotedChat`](../app/chat/piloted.py) · [`AgenticChat`](../app/chat/agentic.py) | [tests/unit/TieredChat](../tests/unit/TieredChat/) · [measured head-to-head](../tests/eval/RESULTS.md) |
