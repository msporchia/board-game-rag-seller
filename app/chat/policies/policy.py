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

Each policy hardcodes ONE concrete behavior, so its effect can be unit-tested in isolation and
stays stable even when other parts of the prompt/pipeline change (the point of the design).
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
