"""ChatGraph + CustomerContext — the Phase 6 split through the stateful path.

Purpose: lock that `customer_context` passed to ChatGraph.reply reaches the generate node and
the enforced-vs-generated split applies end-to-end on the stateful engine (not just Phase 4):
an owned game is dropped from the cards, and the context is checkpointed on the session.
How: in-memory checkpointer, fake analyzer/generation LLMs + fake retriever (see conftest).
"""

from app.chat.models.customer_context import CustomerContext
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.ChatGraph.fakes import make_hit


class TestChatGraphCustomerContext:
    def test_received_game_is_excluded_on_the_stateful_path(self, make_graph):
        hits = [make_hit(1, "Alpha"), make_hit(2, "Bravo"), make_hit(3, "Charlie")]
        reply = ChatReply(
            intro="Ecco.",
            recommendations=[ChatRecommendation(id=2, pitch="Bravo, già tuo."),
                             ChatRecommendation(id=3, pitch="Charlie ti piacerà.")],
        )
        graph, _, _, _ = make_graph(hits=hits, reply=reply)

        res = graph.reply("qualcosa", session_id="s1",
                          customer_context=CustomerContext(received_products=[2]))

        assert 2 not in [g.id_product for g in res.games]
        assert "Bravo" not in res.message
