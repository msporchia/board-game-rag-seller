# SEL-148 — Chat cost control: daily hard-limit + per-session budget

| | |
|---|---|
| **Type** | Feature (Security / Cost) |
| **Area** | api/chat + config |
| **Priority** | High |
| **Reported** | 2026-07-06 |
| **Status** | Open |

## Context

Nobody ships a *local* model to actually sell — it is too weak. The realistic deployment points
the chat at a cheap **paid** model (e.g. Haiku): little per call, but **not zero**. Per-*turn*
bounds exist (`MAX_ROUNDS=3`, `HISTORY_MAX=12`, `message` length cap from SEL-122); the
**cross-turn / per-day** dimension does not. This is the bankruptcy guardrail (SEL-122 P1).

**Trust boundary — this is a multi-tier defence, not all here.** This microservice is **internal**:
it is not exposed to the public internet; the **BFF** (`seller-shop`) is the only caller, and it
holds the user sessions and identity. So the two tiers split by what each one *knows*:

- **BFF (edge, first line)** — owns authn and the anti-spam / anti-DDoS rate limiting, because it
  has the context the seller lacks: it can differentiate **authenticated vs anonymous** callers and
  meter **per user / per session**. Cheapest place to shed abusive volume.
- **Seller (this service, backstop)** — owns the **cost ceiling**, because only it knows the
  token/€ of each call, and as **defence in depth**: a misconfigured, bypassed, or internally-reached
  BFF must still never run up an unbounded bill. This tier does not trust the caller to have limited
  spend.

**Network isolation is the precondition.** The split only holds if the seller genuinely cannot be
reached except through the BFF — and today nothing enforces that. It is a **deployment** control,
not code: the service should sit on a **private network with no public ingress** (on AWS: a private
subnet inside a VPC, no public IP, ingress restricted to the BFF via security group / internal load
balancer). This must be true before a paid model is wired; otherwise the cost backstop is the *only*
line of defence instead of the last.

## Proposed work (seller side — the backstop)

- A configurable **daily cost/token ceiling** and a **per-session budget**. Spend is already
  measurable: the `traces` table records input/output tokens per LLM call
  (`app/core/tracing/handler.py`) — add a per-model price table (Haiku etc.) to turn tokens into cost.
- **Graceful degradation on breach**, never a 500 and never "keep spending": fall back to the
  cheapest local tier or a static honest reply ("sono molto richiesto ora, riprova più tardi").
  A kill-switch, not a soft nudge.
- The seller enforces the ceiling **regardless of caller** — it is the last line before the paid
  model, not a convenience for a well-behaved BFF.

## Companion work (BFF side — not in this repo, does not exist yet)

The edge gate (authn-aware rate limiting, per-session, anon-vs-authenticated quotas, anti-DDoS) is
best implemented on the **BFF** (`seller-shop`) — it has the identity/session context this service
lacks. It is **not specced or built there yet**; this ticket only names the right place for it. Per
the one-session-per-repo rule, write the spec from a `seller-shop` session, not from here — the two
tiers are designed together but shipped in their own repos.

## Why it matters

Defence in depth on the one liability that can end the project: the BFF sheds abusive **volume**
cheaply (it has identity), the seller guarantees the **€ ceiling** no matter what reaches it.
Turns "an abuser wastes our tokens" (SEL-122 P1/P2) from open-ended into bounded — and the ceiling
holds even if the edge tier fails. The showcase already tracks tokens-per-chat
(`docs/showcase/chat.md`); this makes the ceiling real, not just measured.

**Source:** conversation 2026-07-06 (cost/abuse priorities) · **Related:** SEL-122 (threat model),
SEL-113 (circuit breaker), SEL-118 (session lock), SEL-102 (model digest), SEL-103 (token counts),
SEL-149 (cost dashboard) · **Touches:** `app/api/chat.py`, `app/config.py`, `app/core/tracing/`
· **Companion (elsewhere, not yet built):** `seller-shop` edge gate (authn + rate-limit + anti-DDoS)
+ network isolation (private subnet / VPC, no public ingress) — named here, specced & built from a
seller-shop session per the one-session-per-repo rule
