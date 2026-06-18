"""CustomerContext.exclude_owned — the deterministic half of the Phase 6 split.

Purpose: lock that games the customer already owns (`received_products`) are removed from the
hits in code — the model never gets to re-pitch them — while cart/sent ids do NOT remove
anything (they are framed, not enforced; see test_framing_block).
How: pure data, no LLM, no retriever. Build GameHits directly and assert on the filtered list.
"""

from app.chat.models.customer_context import CustomerContext
from app.models.game_hit import GameHit


def hit(id_product: int, name: str) -> GameHit:
    return GameHit(score=0.9, id_product=id_product, name=name)


class TestExcludeOwned:
    def test_drops_received_games(self):
        hits = [hit(1, "Alpha"), hit(2, "Bravo"), hit(3, "Charlie")]
        cc = CustomerContext(received_products=[2])

        kept = cc.exclude_owned(hits)

        assert [h.id_product for h in kept] == [1, 3]

    def test_cart_and_sent_do_not_exclude(self):
        hits = [hit(1, "Alpha"), hit(2, "Bravo")]
        cc = CustomerContext(cart_products=[1], sent_products=[2])

        # Only `received` is enforced deterministically; cart/sent stay on the table.
        assert cc.exclude_owned(hits) == hits

    def test_empty_context_returns_the_hits_unchanged(self):
        hits = [hit(1, "Alpha"), hit(2, "Bravo")]

        assert CustomerContext().exclude_owned(hits) is hits

    def test_received_id_not_in_hits_is_a_no_op(self):
        hits = [hit(1, "Alpha")]

        assert [h.id_product for h in CustomerContext(received_products=[99]).exclude_owned(hits)] == [1]

    def test_is_empty(self):
        assert CustomerContext().is_empty()
        assert not CustomerContext(received_products=[1]).is_empty()
        assert not CustomerContext(cart_products=[1]).is_empty()
        assert not CustomerContext(sent_products=[1]).is_empty()
