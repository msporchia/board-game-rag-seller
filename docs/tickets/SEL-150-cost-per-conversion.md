# SEL-150 — Cost per conversion: tie spend to real outcomes

| | |
|---|---|
| **Type** | Research / Feature |
| **Area** | observability + chat/state |
| **Priority** | Medium |
| **Reported** | 2026-07-06 |
| **Status** | Open |

## Context

We can already price spend (SEL-149) **and** the seller sees commerce outcomes: `CustomerContext`
carries the customer's `cart` / `sent` / `received` product-id sets, derived server-side by the BFF
(`app/chat/models/customer_context.py`). Put together, we can answer the question the showcase only
gestures at today — not "how many tokens per chat" but **"how much did we spend per game actually
added to the cart / bought"**, per engine and per model. The whole stack for this exists; nobody has
connected the two ends.

## Proposed work

- Define the **conversion event** (add-to-cart / order attributed to a session) and **attribute
  spend** to it — the hard part is attribution: which turn(s) caused the add, and over what window.
- Compute **cost-per-conversion / ROI** per engine and per model; feed it into the A/B infra
  (SEL-117) so "the agent converts most but costs most" (`docs/showcase/chat.md`) becomes a
  decidable trade-off, not a narrative.

## Why it matters

A daily cost limit (SEL-148) caps the downside; cost-per-conversion tells you whether the spend is
*worth it* — the difference between "cheap" and "profitable". It also turns the engine choice
(pipeline / piloted / agent / frontier) into a data-driven decision.

## Open questions

- Attribution model (last-turn, whole-session, decay?) and the conversion window.
- Does the BFF expose an order/checkout event, or only the cart/sent snapshots we get per turn?

**Source:** conversation 2026-07-06 (cost priorities) · **Related:** SEL-149 (cost dashboard),
SEL-148 (hard-limit), SEL-117 (A/B infra), SEL-116 (user memory / tier routing) · **Touches:**
`app/chat/models/customer_context.py`, `app/core/tracing/`, `app/api/`
