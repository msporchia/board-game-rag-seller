"""AgenticChat — in-process session memory and the end-of-turn `state()` report (docs/idee.md §Q).

Purpose: a follow-up turn sees the conversation so far (the agent is not piloted — it reads the
whole exchange and chooses its own queries), and `state()` reports the agent's honest end-of-turn
data (last hits + the searches the model ran), with the piloted/pipeline-shaped channels left
None (out of scope for a black-box agent).
"""

from langchain_core.messages import AIMessage

from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.AgenticChat.fakes import make_engine, make_hit, tool_call

_R = ChatReply(intro="ok", recommendations=[ChatRecommendation(id=1, pitch="A!")])


class TestMemory:
    def test_prior_turns_feed_the_next_turn(self):
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "x"}, "1"), AIMessage(content="ok"),
                      tool_call({"query": "y"}, "2"), AIMessage(content="ok")],
            hits_batches=[[make_hit(1, "Alpha")]],
            reply=_R)

        engine.reply("primo messaggio", session_id="s1")
        engine.reply("secondo messaggio", session_id="s1")

        # invocations: [t1r1, t1r2, t2r1, t2r2]; the 2nd turn's first call must carry turn 1.
        second_turn = engine._llm.invocations[2]
        texts = [m.content for m in second_turn]
        assert any("primo messaggio" in t for t in texts)
        assert any("secondo messaggio" in t for t in texts)

    def test_state_reports_last_turn_searches_and_hits(self):
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "cooperativo", "players": 2}), AIMessage(content="ok")],
            hits_batches=[[make_hit(7, "Pandemic")]],
            reply=_R)

        engine.reply("un cooperativo per due", session_id="s1")
        st = engine.state("s1")

        assert st["strategy"] is None and st["filters_spec"] is None  # out of scope for the agent
        assert [h.id_product for h in st["hits"]] == [7]
        assert st["turn_searches"][0]["filters"] == {"players": {"vals": [2]}}

    def test_sessions_are_isolated(self):
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "x"}), AIMessage(content="ok")],
            hits_batches=[[make_hit(1, "A")]], reply=_R)

        engine.reply("ciao", session_id="s1")

        assert engine.state("s2") == {"strategy": None, "filters_spec": None,
                                      "hits": [], "turn_searches": []}
