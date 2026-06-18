"""ChatAdvisor + CustomerContext — the enforced-vs-generated split applied during generation.

Purpose: lock the Phase 6 behavior at the advisor seam every engine funnels through:
  - ENFORCED: a `received` (owned) game is dropped from BOTH cards and message even when the LLM
    explicitly recommends it — same discipline as anti-hallucination grounding, but driven by the
    customer's commerce state rather than the retrieved set.
  - all hits owned → honest no-match (nothing left to pitch, no invented alternative).
  - GENERATED: cart/sent games stay on the table and reach the prompt as a framing instruction.
  - no context → the prompt and result are unchanged (backward compatible).
How: fake retriever + fake structured LLM (see conftest/fakes). No Ollama, no Qdrant.
"""

from app.chat.advisor import _NO_MATCH
from app.chat.models.customer_context import CustomerContext
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.ChatAdvisor.fakes import make_hit


def rec(id: int, pitch: str) -> ChatRecommendation:
    return ChatRecommendation(id=id, pitch=pitch)


class TestChatAdvisorCustomerContext:
    def test_received_game_is_dropped_from_cards_and_message(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo"), make_hit(30, "Charlie")]
        # The model recommends a game the customer already owns (20) — it must not survive.
        reply = ChatReply(
            intro="Ecco cosa ti propongo.",
            recommendations=[rec(20, "Bravo è già tuo ma riproponiamolo."),
                             rec(30, "Charlie vi terrà incollati.")],
        )
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa", customer_context=CustomerContext(received_products=[20]))

        assert [g.id_product for g in res.games] == [30]
        assert "Bravo" not in res.message
        assert "Charlie vi terrà incollati." in res.message

    def test_all_hits_owned_degrades_to_honest_no_match(self, make_advisor):
        hits = [make_hit(1, "Alpha"), make_hit(2, "Bravo")]
        reply = ChatReply(intro="ok", recommendations=[rec(1, "Alpha!"), rec(2, "Bravo!")])
        advisor, _, llm = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa",
                            customer_context=CustomerContext(received_products=[1, 2]))

        # Nothing left after exclusion → the honest no-match, and the LLM is never prompted.
        assert res.message == _NO_MATCH
        assert res.games == []
        assert llm.calls == []

    def test_cart_and_sent_games_stay_and_reach_the_prompt(self, make_advisor):
        hits = [make_hit(1, "Alpha"), make_hit(2, "Bravo")]
        reply = ChatReply(intro="ok", recommendations=[rec(1, "Alpha è perfetto.")])
        advisor, _, llm = make_advisor(hits=hits, reply=reply)

        cc = CustomerContext(cart_products=[1], sent_products=[2])
        res = advisor.reply("qualcosa", customer_context=cc)

        prompt = llm.calls[0]
        assert "CONTESTO CLIENTE" in prompt
        assert "carrello" in prompt and "Alpha" in prompt   # cart framing
        assert "arrivo" in prompt and "Bravo" in prompt      # sent framing
        # Cart/sent are NOT excluded: the model is still free to feature them.
        assert [g.id_product for g in res.games] == [1]

    def test_no_customer_context_leaves_the_prompt_unchanged(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(intro="ok", recommendations=[rec(1, "Alpha!")])
        advisor, _, llm = make_advisor(hits=hits, reply=reply)

        advisor.reply("qualcosa")

        assert "CONTESTO CLIENTE" not in llm.calls[0]
