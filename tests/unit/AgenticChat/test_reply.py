"""AgenticChat — the experimental tool-calling engine (docs/idee.md §Q, Phase 6).

Purpose: lock the loop's contract with the model faked:
  - the model drives search_catalog; the hits it retrieves are grounded by ChatAdvisor.pitch
    (a featured game must have been retrieved — same invariant as every engine);
  - hits from multiple tool calls are UNIONed (deduped by id) before grounding;
  - a turn with NO usable tool call degrades to the honest no-match (no invented games);
  - active policies wrap the generation step (prompt block, forced expertise).
"""

from langchain_core.messages import AIMessage

from app.chat.advisor import ChatAdvisor, _NO_MATCH
from app.chat.agentic import AgenticChat
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.AgenticChat.fakes import (FakePitchLLM, FakeToolCallingLLM, make_engine,
                                          make_hit, tool_call)


class TestReply:
    def test_tool_hits_are_grounded_by_the_pitch(self):
        reply = ChatReply(intro="Ecco.", recommendations=[ChatRecommendation(id=1, pitch="A!")])
        engine, retriever, _ = make_engine(
            scripted=[tool_call({"query": "cooperativo"}), AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "Alpha"), make_hit(2, "Bravo")]],
            reply=reply)

        res = engine.reply("un gioco per la famiglia", session_id="s1")

        assert retriever.calls[0][0] == "cooperativo"   # the model's query reached the catalog
        assert [g.id_product for g in res.games] == [1]  # grounded over what the tool returned

    def test_union_of_tool_calls_feeds_grounding(self):
        # Two rounds searching; overlapping hits are deduped by id before the pitch.
        reply = ChatReply(intro="ok", recommendations=[ChatRecommendation(id=3, pitch="C!")])
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "astratto"}, "1"),
                      tool_call({"query": "strategico"}, "2"), AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "A"), make_hit(2, "B")],
                          [make_hit(2, "B"), make_hit(3, "C")]],
            reply=reply)

        res = engine.reply("qualcosa", session_id="s1")

        assert [g.id_product for g in res.games] == [3]  # id 3 came from the 2nd search

    def test_no_tool_call_degrades_to_honest_no_match(self):
        from app.chat.advisor import _NO_MATCH

        engine, retriever, pitch = make_engine(
            scripted=[AIMessage(content="non cerco nulla")],
            hits_batches=[[make_hit(1, "A")]],
            reply=ChatReply(intro="unused"))

        res = engine.reply("ciao", session_id="s1")

        assert res.message == _NO_MATCH
        assert retriever.calls == [] and pitch.calls == []  # nothing searched, nothing pitched

    def test_tool_failure_does_not_kill_the_turn(self):
        class RaisingRetriever:
            def search(self, *a, **k):
                raise RuntimeError("boom")

        advisor = ChatAdvisor(retriever=RaisingRetriever(),
                              llm=FakePitchLLM(ChatReply(intro="unused")))
        engine = AgenticChat(advisor=advisor, llm=FakeToolCallingLLM(
            [tool_call({"query": "x"}), AIMessage(content="fatto")]))

        res = engine.reply("ciao", session_id="s1")

        # The tool raised; the loop swallowed it and the turn still produced a (no-match) reply.
        assert res.message == _NO_MATCH
        assert engine.last_turn_searches == []  # the failed call left no search record

    def test_policies_shape_the_pitch(self):
        reply = ChatReply(intro="ok", recommendations=[ChatRecommendation(id=1, pitch="A!")])
        engine, _, pitch = make_engine(
            scripted=[tool_call({"query": "regalo"}), AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "Alpha")]],
            reply=reply)

        engine.reply("un regalo", session_id="s1",
                     custom_policy=["christmas_sale", "assume_advanced"])

        assert "saldi di Natale" in pitch.calls[0]
        assert "livello di esperienza: advanced" in pitch.calls[0]
