# SEL-142 — Chat suggests the wrong kind of game for a "cooperative" request

| | |
|---|---|
| **Type** | Bug |
| **Area** | Chat assistant |
| **Severity** | High — customers get wrong suggestions |
| **Found by** | manual testing (shop) |
| **Reported** | 2026-06-18 |
| **Status** | Open |

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
