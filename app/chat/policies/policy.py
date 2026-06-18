"""Base class for a swappable per-turn policy (docs/idee.md §O/§Q).

A policy is OPEN code, not a closed set of declarative hooks: it is composed as MIDDLEWARE
around the turn's stages (PolicySet builds the onion). Each policy overrides only the seams it
cares about; the defaults are pass-through / no-op, so a policy that touches retrieval leaves
generation untouched and vice versa.

Two middleware seams — each receives the live per-stage context and a `call_next` continuation
(the rest of the chain plus the stage's real work). A policy can:
  - mutate `ctx` before calling `call_next` (e.g. widen the query, swap `ctx.retriever`);
  - post-process what `call_next` returns (e.g. drop/reorder hits, rewrite the response);
  - NOT call `call_next` and return its own result (short-circuit the stage entirely).

Two convenience shortcuts — `force_expertise` / `force_strategy` — for the frequent, readable
cases (persona level, selling strategy) that the pipeline graph applies in its analyze/route
nodes, where there is no stage to wrap. They return None to mean "leave the current value".

WHY THIS SHAPE — testability + security (the canonical rationale; facets also in policy_set.py,
docs/chat.md, README, idee.md §O):

  1. SECURITY — no prompt injection. A policy is activated BY NAME from a hardcoded REGISTRY
     (PolicySet), never by the caller injecting prompt text. The wire (a frontend/BFF) picks from
     a closed menu; it cannot smuggle instructions into the model. An unknown name is logged and
     skipped, never an error — a customer turn must not 500 on a typo.
  2. SECURITY — can't break invariants. A policy steers BEHAVIOR; the grounding invariant
     (anti-hallucination) lives in CODE (ChatAdvisor.pitch), not in a policy, so no policy can make
     the bot recommend a game that wasn't retrieved. "Extensible" stays "safe": a policy reorders
     hits or reshapes the prompt, it never disables a guarantee.
  3. TESTABILITY / measurability. One class = one concrete behavior → unit-testable in isolation,
     and its effect stays STABLE when the rest of the prompt/pipeline changes (the stability
     tests). The active policy names are logged per node, so each turn is measurable / A/B-able.
"""

from abc import ABC
from typing import TYPE_CHECKING, Callable, ClassVar

if TYPE_CHECKING:
    from app.chat.models.response import ChatResponse
    from app.chat.models.strategy import Strategy
    from app.chat.policies.generation_context import GenerationContext
    from app.chat.policies.retrieval_context import RetrievalContext
    from app.models.game_hit import GameHit


class Policy(ABC):
    name: ClassVar[str]
    description: ClassVar[str]

    def around_retrieve(self, ctx: "RetrievalContext",
                        call_next: "Callable[[RetrievalContext], list[GameHit]]"
                        ) -> "list[GameHit]":
        """Wrap the retrieval stage. Default: run it unchanged."""
        return call_next(ctx)

    def around_generate(self, ctx: "GenerationContext",
                       call_next: "Callable[[GenerationContext], ChatResponse]"
                       ) -> "ChatResponse":
        """Wrap the generation stage. Default: run it unchanged."""
        return call_next(ctx)

    def force_expertise(self, current: str | None) -> str | None:
        """Override the assumed expertise level for this turn (None = leave as is)."""
        return None

    def force_strategy(self, current: "Strategy") -> "Strategy | None":
        """Override the selling strategy for this turn (None = leave to the router)."""
        return None
