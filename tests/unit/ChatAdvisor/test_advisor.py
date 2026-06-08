"""ChatAdvisor — the RAG generation step (Phase 4, stateless).

Purpose: lock the advisor's two invariants and its contract, with the model faked.
What it tests:
  - Anti-hallucination grounding: featured games are exactly the retrieved ids the LLM cited,
    invalid/invented ids are dropped, LLM order is preserved.
  - Honest empty-retrieval path (no LLM call, no invented alternatives).
  - Robust transport: an LLM failure falls back to a deterministic reply, never an exception.
  - Contract shape: message passes through, quick_replies are capped, choices reach retrieval.
How: fake retriever (preset hits) + fake structured LLM (preset ChatReply or raising), both
local to this unit (see conftest). No Ollama, no Qdrant.
"""

from app.chat.advisor import _NO_MATCH
from app.chat.models import ChatReply

from .conftest import make_hit


class TestChatAdvisor:
    def test_grounding_drops_unretrieved_ids(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo"), make_hit(30, "Charlie")]
        reply = ChatReply(message="ok", recommended_ids=[20, 999], quick_replies=[])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # 999 was never retrieved → it cannot reach the response (anti-hallucination).
        assert [g.id_product for g in res.games] == [20]

    def test_grounding_preserves_llm_order(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo"), make_hit(30, "Charlie")]
        reply = ChatReply(message="ok", recommended_ids=[30, 10])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        assert [g.id_product for g in res.games] == [30, 10]

    def test_empty_retrieval_is_honest(self, make_advisor):
        advisor, _, llm = make_advisor(hits=[], reply=ChatReply(message="unused"))

        res = advisor.reply("gioco inesistente")

        assert res.message == _NO_MATCH
        assert res.games == []
        assert llm.calls == []  # no point prompting the LLM with zero games

    def test_llm_failure_falls_back_to_top_hits(self, make_advisor):
        hits = [make_hit(i, f"G{i}") for i in (1, 2, 3, 4, 5)]
        advisor, _, _ = make_advisor(hits=hits, raises=True)

        res = advisor.reply("qualcosa")

        # Deterministic fallback over the top-3 hits, never a 500.
        assert [g.id_product for g in res.games] == [1, 2, 3]
        assert res.games[0].name in res.message

    def test_no_valid_picks_surfaces_top_hits(self, make_advisor):
        hits = [make_hit(i, f"G{i}") for i in (1, 2, 3, 4)]
        reply = ChatReply(message="vedi qui", recommended_ids=[999])  # all invalid
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        assert [g.id_product for g in res.games] == [1, 2, 3]

    def test_quick_replies_capped_at_three(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(message="ok", recommended_ids=[1],
                          quick_replies=["a", "b", "c", "d", "e"])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        assert res.quick_replies == ["a", "b", "c"]

    def test_message_passes_through(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(message="Ti consiglio Alpha!", recommended_ids=[1])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        assert advisor.reply("qualcosa").message == "Ti consiglio Alpha!"

    def test_choices_are_folded_into_the_query(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(message="ok", recommended_ids=[1])
        advisor, retriever, _ = make_advisor(hits=hits, reply=reply)

        advisor.reply("cooperativo", choices=["Max 1 ora"])

        query = retriever.calls[0][0]
        assert "cooperativo" in query and "Max 1 ora" in query
