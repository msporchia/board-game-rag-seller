"""PolicySet — resolve a list of policy NAMES into composed middleware (docs/idee.md §O/§Q).

The caller sends `custom_policy: ["christmas_sale", "promote_cooperative"]`; we look each name up
in `REGISTRY` (hardcoded, one entry per file — the same shape as `SearchFilters.REGISTRY`) and
compose the resolved policies as an ONION around a turn's stage: `run_retrieve`/`run_generate`
take the stage's real work (`base`) and wrap it inside each policy's `around_*`, the first policy
outermost. The two shortcuts (`force_expertise`/`force_strategy`) fold over the policies in order.

Unknown names are logged and skipped, NOT raised (a customer turn must never 500 on a caller
typo) — unlike `SearchFilters.from_dict`, whose names come from a validated model, not the wire.
The active names are exposed via `names` so every node can log which policies shaped the turn
(measurability: that is what makes per-policy A/B and stability checks possible).
"""

from typing import Callable

from app.chat.models.response import ChatResponse
from app.chat.models.strategy import Strategy
from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.library.assume_advanced import AssumeAdvanced
from app.chat.policies.library.christmas_sale import ChristmasSale
from app.chat.policies.library.force_quick_match import ForceQuickMatch
from app.chat.policies.library.promote_cooperative import PromoteCooperative
from app.chat.policies.policy import Policy
from app.chat.policies.retrieval_context import RetrievalContext
from app.core.logging import get_logger
from app.models.game_hit import GameHit

log = get_logger(__name__)

# name (as sent in `custom_policy`) → concrete Policy class. Hardcoded, one entry per file in
# `library/` (the wiring lives here in `policies/`, the actual policies live there).
REGISTRY: dict[str, type[Policy]] = {
    "christmas_sale": ChristmasSale,
    "promote_cooperative": PromoteCooperative,
    "assume_advanced": AssumeAdvanced,
    "force_quick_match": ForceQuickMatch,
}


class PolicySet:
    def __init__(self, policies: list[Policy]):
        self.policies = policies

    @classmethod
    def from_names(cls, names: list[str] | None) -> "PolicySet":
        policies: list[Policy] = []
        for name in names or []:
            klass = REGISTRY.get(name)
            if klass is None:
                log.warning("unknown_policy_skipped", policy=name)
                continue
            policies.append(klass())
        return cls(policies)

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.policies]

    def is_empty(self) -> bool:
        return not self.policies

    # ---- middleware composition ---------------------------------------------------

    def run_retrieve(self, ctx: RetrievalContext,
                     base: Callable[[RetrievalContext], list[GameHit]]) -> list[GameHit]:
        chain = base
        for policy in reversed(self.policies):
            chain = self._wrap(policy.around_retrieve, chain)
        return chain(ctx)

    def run_generate(self, ctx: GenerationContext,
                     base: Callable[[GenerationContext], ChatResponse]) -> ChatResponse:
        chain = base
        for policy in reversed(self.policies):
            chain = self._wrap(policy.around_generate, chain)
        return chain(ctx)

    @staticmethod
    def _wrap(around: Callable, call_next: Callable) -> Callable:
        """One onion layer: bind `call_next` so the policy receives only the context."""
        return lambda ctx: around(ctx, call_next)

    # ---- shortcuts ----------------------------------------------------------------

    def force_expertise(self, current: str | None) -> str | None:
        for policy in self.policies:
            current = policy.force_expertise(current) or current
        return current

    def force_strategy(self, current: Strategy) -> Strategy:
        for policy in self.policies:
            current = policy.force_strategy(current) or current
        return current
