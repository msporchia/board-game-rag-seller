# SEL-142 — Chat suggests the wrong kind of game for a "cooperative" request

| | |
|---|---|
| **Type** | Bug |
| **Area** | Chat assistant |
| **Severity** | High — customers get wrong suggestions |
| **Found by** | manual testing (shop) |
| **Reported** | 2026-06-18 |
| **Status** | Resolved (2026-06-23) |

## What happens

I was trying the chat like a customer would. I asked for a **cooperative** game and it
suggested games that are not cooperative at all — the kind where everyone plays against each
other. It clearly didn't pick up that I wanted a game where you all play together.

## How to see it

Open the chat and write, as a customer would:

> voglio un gioco cooperativo come Le Cronache di Avel, cosa mi consigli?

(*Le Cronache di Avel* is just an example the customer mentions — we don't sell it. The point is
they want a cooperative game.)

## What I expected

Suggestions that are actually cooperative games. We do sell several (the two *Pandemic* boxes,
*Massive Darkness*, *Le Case della Follia*, and a few more), so there's plenty to recommend.

## What I got instead

It proposed competitive games (things like *Wingspan*, *Catan*, *Carcassonne*) and talked about
them as if they were a good match. They're nice games, but they are not cooperative — it's the
opposite of what was asked.

## Why it matters

Cooperative vs "everyone for themselves" is a big deal for customers — it changes how the whole
evening goes. If someone asks for cooperative and we hand them the opposite, they lose trust in
the suggestions. It probably isn't only about the word "cooperative" either — I'd worry the same
happens with other things people ask for.

## Done when

When a customer asks for a cooperative game, the games suggested are actually cooperative.

## Resolution (2026-06-23)

`cooperative` is now a first-class, **tri-state** structured field (True / False / None) instead of
a loose tag retrieval could only nudge:

- **Data** — `GameData.cooperative`. An explicit catalog co-op tag/category is a deterministic
  shortcut (`mentions_cooperative`); otherwise the `CuratorEnricher` **infers** the mode from the
  description — a *semantic* verdict, not a keyword/verbatim match, so a co-op game that never uses
  the word is still caught — and abstains to `None` when unsure.
- **Filter** — `CooperativeFilter`, a hard tri-state `BoolFilter`, registered in the SearchFilters
  REGISTRY and indexed in the payload (`True` → cooperative, `False` → competitive).
- **Chat** — `SearchIntent.cooperative` → `to_filters_spec` (True→cooperative, False→competitive,
  null→no constraint), wired into the piloted/agentic engines, the `search_catalog` tool, the
  `/search` API, and the `INTENT`/`SEARCH_CATALOG` prompts. `PromoteCooperative` now keys off the
  flag as its single source of truth.
- **Tests** — unit coverage including the "hide the catalog tag, recover the verdict via inference
  against the oracle" cross-test, and the filter exercised against an in-memory Qdrant.

**Done-when** is met for the explicit, paraphrase, and known-reference cases.

Spawned follow-ups:

- **[SEL-120](../SEL-120-cooperative-inference-prompt-design.md)** — whether the dedicated inference
  call is justified or the verdict should fold into the existing curator prompt (plus scoring the
  verdict in the Curator eval).
- **[SEL-143](../SEL-143-cooperative-fabricated-from-unknown-reference.md)** — found while testing this
  fix: the intent step can *fabricate* a confident `cooperative=False` from an unknown reference
  game ("come Le Cronache di Avel"), which a hard filter then turns into the opposite of what the
  customer wants. Tracks the remaining unknown-reference gap.

> **Note:** already-indexed games carry no `cooperative` value until **re-ingested** — there is no
> backfill. This is an R&D project, so no data migration path is provided: the flag lands on the
> next full ingest.
