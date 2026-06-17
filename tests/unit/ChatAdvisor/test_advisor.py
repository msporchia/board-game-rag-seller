"""ChatAdvisor — the RAG generation step (Phase 4, stateless).

Purpose: lock the advisor's two invariants and its contract, with the model faked.
What it tests:
  - Anti-hallucination grounding: featured games are exactly the retrieved ids the LLM cited;
    a recommendation with an invented id is dropped from BOTH the cards and the assembled
    message (its pitch goes with it); LLM order is preserved; a duplicated id keeps only its
    first citation (found live by the ChatConversation eval: the 8B pitched a game twice).
  - Coherence by construction: the customer message is assembled in code as intro + the pitch
    of each surviving recommendation, in LLM order.
  - Honest empty-retrieval path (no LLM call, no invented alternatives).
  - Robust transport: an LLM failure — or a reply where NO id survives validation — falls back
    to the deterministic reply over the top hits, never an exception.
  - Contract shape: quick_replies are capped, choices reach retrieval.
How: fake retriever (preset hits) + fake structured LLM (preset ChatReply or raising), both
local to this unit (see conftest). No Ollama, no Qdrant.
"""

from app.chat.advisor import _NO_MATCH
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.ChatAdvisor.fakes import make_hit


def rec(id: int, pitch: str) -> ChatRecommendation:
    return ChatRecommendation(id=id, pitch=pitch)


class TestChatAdvisor:
    def test_grounding_drops_unretrieved_ids_from_cards_and_message(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo"), make_hit(30, "Charlie")]
        reply = ChatReply(
            intro="Ecco cosa ti propongo.",
            recommendations=[rec(20, "Bravo è perfetto in due."),
                             rec(999, "Fantasma vi stupirà.")],
        )
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # 999 was never retrieved → its card AND its pitch cannot reach the response.
        assert [g.id_product for g in res.games] == [20]
        assert "Fantasma" not in res.message
        assert "Bravo è perfetto in due." in res.message

    def test_grounding_preserves_llm_order(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo"), make_hit(30, "Charlie")]
        reply = ChatReply(recommendations=[rec(30, "p3"), rec(10, "p1")])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        assert [g.id_product for g in res.games] == [30, 10]

    def test_duplicate_ids_keep_first_citation_only(self, make_advisor):
        hits = [make_hit(10, "Alpha"), make_hit(20, "Bravo")]
        reply = ChatReply(
            intro="Ecco.",
            recommendations=[rec(10, "Alpha è perfetto."), rec(20, "Bravo è veloce."),
                             rec(10, "Alpha, di nuovo!")],
        )
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # The same game can be cited once: the duplicate card AND its second pitch are dropped.
        assert [g.id_product for g in res.games] == [10, 20]
        assert "di nuovo" not in res.message

    def test_message_is_intro_plus_surviving_pitches_in_order(self, make_advisor):
        hits = [make_hit(1, "Alpha"), make_hit(2, "Bravo")]
        reply = ChatReply(
            intro="Ho due idee per voi.",
            recommendations=[rec(2, "Bravo è veloce e brillante."),
                             rec(1, "Alpha vi terrà incollati.")],
        )
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # Assembled in code: intro first, then the pitches in the LLM's order — the text can
        # only describe the games in the cards (coherence by construction).
        assert res.message == "Ho due idee per voi. Bravo è veloce e brillante. Alpha vi terrà incollati."
        assert [g.id_product for g in res.games] == [2, 1]

    def test_empty_retrieval_is_honest(self, make_advisor):
        advisor, _, llm = make_advisor(hits=[], reply=ChatReply(intro="unused"))

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

    def test_all_ids_invalid_degrades_to_deterministic_fallback(self, make_advisor):
        hits = [make_hit(i, f"G{i}") for i in (1, 2, 3, 4)]
        reply = ChatReply(intro="vedi qui", recommendations=[rec(999, "invented")])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # No surviving pitch → nothing grounded to say. Same degradation as a transport failure:
        # the deterministic reply over the top hits, so message and cards still match.
        assert [g.id_product for g in res.games] == [1, 2, 3]
        assert res.games[0].name in res.message
        assert "invented" not in res.message

    def test_quick_replies_capped_at_three(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(intro="ok", recommendations=[rec(1, "Alpha!")],
                          quick_replies=["a", "b", "c", "d", "e"])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        assert res.quick_replies == ["a", "b", "c"]

    def test_blank_intro_and_pitches_fall_back_to_plain_pitch(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(intro="  ", recommendations=[rec(1, "")])
        advisor, _, _ = make_advisor(hits=hits, reply=reply)

        res = advisor.reply("qualcosa")

        # Valid id but empty text → cards stay, message degrades to the deterministic pitch.
        assert [g.id_product for g in res.games] == [1]
        assert "Alpha" in res.message

    def test_choices_are_folded_into_the_query(self, make_advisor):
        hits = [make_hit(1, "Alpha")]
        reply = ChatReply(intro="ok", recommendations=[rec(1, "Alpha!")])
        advisor, retriever, _ = make_advisor(hits=hits, reply=reply)

        advisor.reply("cooperativo", choices=["Max 1 ora"])

        query = retriever.calls[0][0]
        assert "cooperativo" in query and "Max 1 ora" in query

    def test_custom_policy_shapes_the_prompt_without_bypassing_grounding(self, make_advisor):
        hits = [make_hit(4, "Pandemic"), make_hit(7, "Splendor")]
        reply = ChatReply(intro="ok", recommendations=[rec(4, "Pandemic è perfetto.")])
        advisor, _, llm = make_advisor(hits=hits, reply=reply)

        res = advisor.reply(
            "un regalo per Natale",
            custom_policy=["christmas_sale", "assume_advanced", "force_quick_match"],
        )

        prompt = llm.calls[0]
        assert "saldi di Natale" in prompt           # christmas_sale (around_generate block)
        assert "livello di esperienza: advanced" in prompt  # assume_advanced (force_expertise)
        assert "Strategia per questo turno — QUICK MATCH" in prompt  # force_quick_match
        # Grounding still holds: the model cited only id 4, so only 4 reaches the cards.
        assert [g.id_product for g in res.games] == [4]
