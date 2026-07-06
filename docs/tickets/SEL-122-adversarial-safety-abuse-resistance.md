# SEL-122 — Adversarial safety / abuse-resistance: threat model, role separation, red-team eval

| | |
|---|---|
| **Type** | Research / Feature (Security) |
| **Area** | chat/agent |
| **Priority** | Medium |
| **Reported** | 2026-07-06 |
| **Status** | In progress |

## Context

"How do you protect the model?" is a standard question for any LLM-facing system, and the honest
answer so far was *we never wrote it down*. This ticket owns the analysis and a **first hardening
pass** — it is a strategy and a starting posture, not a claim that the system is "safe". Part of
the task's scope is to keep enumerating other attack classes (see the list below) and to spin off a
new ticket whenever one warrants its own work.

**Threat model — abuse, not confidentiality.** This service holds **no secrets**: the prompts are
in the repo, the catalog is a shop catalog, there is no privileged data the model could leak. So
the goal is **not** to defend a system prompt or resist extraction. The goal is to keep the seller
from being **abused** — turned into a free general-purpose LLM, made to fabricate a product / price
/ availability, or steered out of its role by text in a customer turn. Different models fail
differently (the weak local 8B has essentially no self-defence; the frontier tier has more), so the
guarantee must live in **structure and code**, invariant across models — never in the model's
willpower.

## Current mitigations we lean on (not a proof of safety)

Several structural properties already narrow the *commercial* outcome of a compromised turn. They
are the reason we can start conservative rather than bolt on a moderation layer — but they are a
**working assumption**, not a guarantee, and only cover the attack classes we have thought about so
far:

- **Grounding invariant** — `ChatAdvisor.pitch` drops any recommendation whose `id` was not
  retrieved, together with its pitch (`app/chat/advisor.py`). This is what keeps a model that
  invents a game/price/stock from surfacing it — the mitigation we lean on most.
- **Read-only surface** — the only model-driven action is `SearchCatalogTool` (retrieval); there
  are no write/side-effecting tools.
- **Output assembled in code** — the customer message is built from `intro` + surviving pitches
  (`advisor.py`), so the model cannot emit an arbitrary free-form reply as the whole turn.
- **Closed policy registry** — policies activate BY NAME from a hardcoded set; the wire cannot
  smuggle instructions through the policy channel (`app/chat/policies/policy.py`).

Our current reading is that this keeps the **blast radius of a *known* jailbreak** modest — at worst
off-topic prose — which is why this pass does **not** add a leaky regex/blocklist that would buy
false confidence. That reading holds only for the vectors below that we've considered; the "Other
attack surfaces" section is where it gets stress-tested, and it may well move.

## The gap this ticket closes

1. **No instruction/data separation on the pitch path.** `ChatAdvisor._prompt` built a single
   string in which the untrusted customer turn was interpolated *above* the grounding rules, and
   `.invoke(str)` delivered the whole thing as one `HumanMessage` — no system role at all. This is
   the path **every** engine uses for its final generation (the agent searches with roles, then
   pitches through here).
2. **User text unbounded.** `ChatRequest.message` had no length cap (`app/chat/models/request.py`).
3. **No scope note.** Nothing told the model to stay a board-game clerk on an off-topic turn (UX,
   not a security boundary).
4. **No proof.** All 15 `ChatConversation` cases are *commercially* adversarial (constraint
   reversals, distractors); none are *security* adversarial. The docs already use the word
   "adversarial" for the bench — this ticket earns the second meaning.

## Work in this pass

- **Role separation on the pitch path** — `_prompt` returns `[SystemMessage(instructions + trusted
  data), HumanMessage(the raw customer turn)]`. The prompt **text is unchanged**; only the routing
  into roles changes, so behaviour risk is minimal. The role boundary *is* the delimiter (best
  practice: the untrusted turn lives in its own role, not interpolated among the rules).
- **Anti-injection + scope lines** in `GROUNDING_RULES` (`app/chat/prompts.py`): the customer turn
  is data to satisfy, never instructions; stay in the board-game-clerk role on off-topic turns.
  Soft by design — a stronger model honours it more, a weaker one leans on the code invariant.
- **Input length cap** on `ChatRequest.message`.
- **Adversarial unit tests** (`tests/unit/ChatAdvisor/test_adversarial.py`, deterministic, offline):
  they simulate a *compromised* model via the fake and assert the code containment holds —
  injection cannot add an unretrieved game, and the customer turn is isolated in its own role with
  the instructions kept in the system role. These test **our** guarantee, not the model's willpower.

## Other attack surfaces to consider (open — spin off tickets as they earn it)

This pass covered the single-turn injection / off-topic / product-fabrication vector on the pitch
path. The following are **not** covered and are explicitly in scope for the ongoing analysis; each
becomes its own `SEL` ticket if it warrants work:

- **Indirect / stored prompt injection via retrieved content.** Game descriptions are enriched from
  the web and land in the SystemMessage as *trusted* data. A poisoned description ("ignore your
  rules…") is an injection we currently treat as trusted — arguably the highest-value vector to
  study next, and it touches the ingestion pipeline, not just chat.
- **Multi-turn / history injection.** Only the *current* turn is role-isolated; prior turns are
  replayed as text. An injection planted on an earlier turn may still ride along.
- **Tool-argument abuse / cost.** Search flooding, pathological args, or many rounds driving up
  cost — overlaps SEL-113 (search-budget circuit breaker).
- **Obfuscation.** Unicode/homoglyph/base64/lookalike encodings of an injection that slip past the
  plain-text rule (cross-ref SEL-108 unicode normalization).
- **Quick-reply / policy-name / customer-context tampering** from the wire (BFF) — the fields the
  frontend controls.
- **Information disclosure** — low harm by design: no secrets (the rules are public, internal
  `id_product` are meaningless outside). The one variant that *would* matter — internal commercial
  data (margin/cost) in the prompt — is designed out: margins are computed behind a hard API
  outside the LLM's reach, and only a **relative priority score (1–5, ranked across games)** ever
  reaches the model. So a leak is irrelevant-to-near-irrelevant, and the residual work is only to
  *enforce* that boundary (no raw commercial field in the prompt context), not to filter output.
- **PII in the turn** and **toxic/unsafe output** — content handling we do nothing about today.
- **Model-specific jailbreaks across the tier** — the weak 8B, the strong local model, and the
  frontier model fail differently; a red-team that passes on one may not on another.
- **DoS via oversized/complex turns** — partially blunted by the new input cap, not measured.

## Deferred (design sketched, not built)

- **`GuardrailPolicy`** — a real pre-turn classifier/moderation stage. The middleware seam already
  exists (`around_generate`/`around_retrieve` in `policy.py`), so it slots in cleanly. Deferred on
  purpose: it adds latency + a model dependency + probabilistic FP/FN to defend a blast radius that
  is already small. Revisit only if we want to *showcase* a moderation layer.
- **Real-model red-team eval** — a handful of `ChatConversation` fixtures (injection, off-topic,
  price-fabrication attempt) scored on Ollama. Stochastic + needs the stack, so it rides the eval
  harness, not the deterministic unit gate.

## Acceptance

The deterministic unit gate proves the structural invariants (isolation of the customer turn;
grounding survives a simulated compromise). The prompt text is byte-identical apart from the added
rule lines, and the existing `ChatConversation` / `ChatPitch` numbers are re-run and recorded as a
ledger row (before → after) — no silent behaviour change.

**Source:** conversation 2026-07-06 (security review) · **Related:** SEL-113 (agent hardening /
circuit breaker), SEL-143 (fabricated hard verdict), SEL-110 (LLM transport) · **Touches:**
`app/chat/advisor.py`, `app/chat/prompts.py`, `app/chat/models/request.py`,
`tests/unit/ChatAdvisor/`
