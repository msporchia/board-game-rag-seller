"""CustomerContext.framing_block — the generated half of the Phase 6 split.

Purpose: lock that cart/sent games that are on the table this turn produce a prompt instruction
telling the model to treat them as already-chosen / on-the-way (not fresh ideas), that only
games actually in `hits` are named, and that nothing → no block (None).
How: pure data, no LLM. Assert on the returned instruction text.
"""

from app.chat.models.customer_context import CustomerContext
from app.models.game_hit import GameHit


def hit(id_product: int, name: str) -> GameHit:
    return GameHit(score=0.9, id_product=id_product, name=name)


class TestFramingBlock:
    def test_cart_games_are_framed_as_already_chosen(self):
        hits = [hit(1, "Alpha"), hit(2, "Bravo")]
        block = CustomerContext(cart_products=[1]).framing_block(hits)

        assert block is not None
        assert "Alpha" in block and "carrello" in block
        assert "Bravo" not in block  # not in the cart

    def test_sent_games_are_framed_as_on_the_way(self):
        hits = [hit(5, "Echo")]
        block = CustomerContext(sent_products=[5]).framing_block(hits)

        assert block is not None
        assert "Echo" in block and "arrivo" in block

    def test_only_games_on_the_table_are_named(self):
        # A cart game that was not retrieved this turn has no card to talk over → not named.
        block = CustomerContext(cart_products=[99]).framing_block([hit(1, "Alpha")])

        assert block is None

    def test_no_cart_or_sent_returns_none(self):
        assert CustomerContext(received_products=[1]).framing_block([hit(1, "Alpha")]) is None
