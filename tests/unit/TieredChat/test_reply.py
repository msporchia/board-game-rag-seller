"""TieredChat — the engine-tier seam (docs/idee.md §Q).

Purpose: lock the degradation contract before any primary engine exists.
What it tests:
  - Empty primary slot (today's production wiring): everything goes to the fallback.
  - A healthy primary answers and the fallback is never touched.
  - ANY primary exception degrades to the fallback — same turn, same arguments — and the
    customer still gets a reply.
How: two FakeEngine instances (preset response or raising), no LLM, no graph.
"""

from app.chat.models.customer_context import CustomerContext
from app.chat.models.response import ChatResponse
from app.chat.tiered import TieredChat

from tests.unit.TieredChat.fakes import FakeEngine


class TestReply:
    def test_empty_primary_slot_goes_to_fallback(self):
        fallback = FakeEngine()
        engine = TieredChat(fallback=fallback)

        res = engine.reply("ciao", choices=["per 2 giocatori"], k=3, session_id="s1")

        assert res is fallback.response
        # The contract travels intact down the ladder.
        assert fallback.calls == [{"message": "ciao", "choices": ["per 2 giocatori"],
                                   "k": 3, "session_id": "s1",
                                   "custom_policy": None, "customer_context": None}]

    def test_healthy_primary_answers_and_fallback_is_untouched(self):
        primary = FakeEngine(response=ChatResponse(message="dal primario", games=[],
                                                   quick_replies=[]))
        fallback = FakeEngine()
        engine = TieredChat(fallback=fallback, primary=primary)

        res = engine.reply("ciao")

        assert res.message == "dal primario"
        assert fallback.calls == []

    def test_primary_failure_degrades_to_fallback_with_same_arguments(self):
        primary = FakeEngine(raises=True)
        fallback = FakeEngine()
        engine = TieredChat(fallback=fallback, primary=primary)

        cc = CustomerContext(received_products=[7])
        res = engine.reply("ciao", choices=["max 30 minuti"], k=4, session_id="s2",
                           custom_policy=["christmas_sale"], customer_context=cc)

        # The primary was tried, the failure never surfaced, the fallback got the SAME turn —
        # including the customer_context, so a degraded turn keeps the Phase 6 split.
        assert res is fallback.response
        assert primary.calls == fallback.calls == [{"message": "ciao",
                                                    "choices": ["max 30 minuti"],
                                                    "k": 4, "session_id": "s2",
                                                    "custom_policy": ["christmas_sale"],
                                                    "customer_context": cc}]
