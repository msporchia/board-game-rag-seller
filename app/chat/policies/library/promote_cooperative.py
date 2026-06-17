"""PromoteCooperative — a retrieval-stage policy that puts itself in the middle of the fetch.

The showcase of an OPEN, fetch-intercepting policy (the shape a `promotions=true` policy would
take once the catalog carries a promo flag — here on real `categoria`/`tags` data instead):

  - BEFORE the fetch: bias the embedding query toward cooperative games (mutates `ctx.query`);
  - AFTER the fetch: bring cooperative hits to the front (stable sort — original order kept
    within each group), so the games on the table lead with the co-op picks.

Its effect is observable on the hits regardless of any prompt wording, so a test can assert it
stays stable while the rest of the prompt/pipeline changes.
"""

from app.chat.policies.policy import Policy
from app.chat.policies.retrieval_context import RetrievalContext
from app.models.game_hit import GameHit

_QUERY_BIAS = "gioco cooperativo, si gioca tutti insieme contro il gioco"


class PromoteCooperative(Policy):
    name = "promote_cooperative"
    description = "Bias retrieval toward cooperative games: query nudge + co-op hits to the front."

    def around_retrieve(self, ctx: RetrievalContext, call_next):
        ctx.query = f"{ctx.query}\n{_QUERY_BIAS}"
        hits = call_next(ctx)
        return sorted(hits, key=lambda h: not self._is_cooperative(h))

    @staticmethod
    def _is_cooperative(hit: GameHit) -> bool:
        haystack = " ".join([hit.categoria or "", *(hit.tags or [])]).lower()
        return "cooperativ" in haystack
