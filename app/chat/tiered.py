"""TieredChat — the seam where chat engine tiers meet (docs/idee.md §Q).

One stable contract — `reply(message, choices, k, session_id) -> ChatResponse` — and two
slots: a `primary` engine that MAY fail and a `fallback` engine that must not. A primary
failure never reaches the customer: any exception falls through to the fallback, logged.
This generalizes the model-tiering already inside the graph ("swap the model on one node")
to "swap the whole path".

Today the primary slot is empty: the API wires TieredChat around ChatGraph so the seam
exists and is exercised, and the future agentic engine (strong model driving a search tool)
plugs in here — together with the circuit breaker (idee.md §Q) that stops paying for a
primary that keeps failing. The degradation ladder then reads: agent → pipeline →
deterministic reply (the fallback already inside ChatAdvisor.pitch).
"""

from app.chat.models.response import ChatResponse
from app.core.logging import get_logger

log = get_logger(__name__)


class TieredChat:
    """`primary` and `fallback` are any objects honoring the ChatGraph.reply contract."""

    def __init__(self, fallback, primary=None):
        self._fallback = fallback
        self._primary = primary

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default") -> ChatResponse:
        """One turn on the primary engine when present, degrading to the fallback on ANY
        primary failure — the customer always gets a reply from somewhere down the ladder."""
        if self._primary is not None:
            try:
                return self._primary.reply(message, choices=choices, k=k,
                                           session_id=session_id)
            except Exception:  # noqa: BLE001 — a primary failure must never kill the turn
                log.warning("primary_engine_degraded", session_id=session_id)
        return self._fallback.reply(message, choices=choices, k=k, session_id=session_id)
