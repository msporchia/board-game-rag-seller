"""CustomerContext.is_empty — whether any commerce state is present this turn.

(The owned-game EXCLUSION is no longer a CustomerContext method: it moved to retrieval —
`received_products` → `RetrievalContext.exclude_ids` → Qdrant `must_not` — and is covered
end-to-end by the engine customer_context tests. CustomerContext now only holds the id sets and
the cart/sent framing.)
"""

from app.chat.models.customer_context import CustomerContext


class TestIsEmpty:
    def test_empty_context(self):
        assert CustomerContext().is_empty()

    def test_any_set_makes_it_non_empty(self):
        assert not CustomerContext(received_products=[1]).is_empty()
        assert not CustomerContext(cart_products=[1]).is_empty()
        assert not CustomerContext(sent_products=[1]).is_empty()
