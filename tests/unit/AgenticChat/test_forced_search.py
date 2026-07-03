"""AgenticChat — the forced-search floor (SEL-147).

Live recordings showed the local model stops emitting tool calls after a few turns, which
collapsed those turns into a FALSE honest no-match: the catalog stocked what was asked, nobody
searched. The contract under test: when a turn produces NO model-driven search, the code runs
one plain search with the customer's own words (flagged `forced`) before the turn may give up;
when the model does search, the floor stays out of the way.
"""

from langchain_core.messages import AIMessage

from app.chat.models.reply import ChatReply
from tests.unit.AgenticChat.fakes import make_engine, make_hit, tool_call

_REPLY = ChatReply(intro="Ecco!", recommendations=[{"id": 7, "pitch": "Perfetto per voi."}],
                   quick_replies=[])


class TestForcedSearch:
    def test_no_tool_call_turn_still_searches(self):
        """The model never calls the tool → the code searches with the raw message, the turn
        ends grounded in real hits instead of a false no-match."""
        engine, retriever, _ = make_engine(
            scripted=[AIMessage(content="ho già in mente qualcosa")],  # no tool_calls, ever
            hits_batches=[[make_hit(7, "Magic Maze")]],
            reply=_REPLY)
        response = engine.reply("un gioco cooperativo per due", session_id="s")
        assert [s.get("forced") for s in engine.last_turn_searches] == [True]
        assert engine.last_turn_searches[0]["query"] == "un gioco cooperativo per due"
        assert [g.id_product for g in response.games] == [7]

    def test_model_driven_search_keeps_the_floor_out(self):
        """When the model does search, no forced record is appended."""
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "cooperativo"}), AIMessage(content="fatto")],
            hits_batches=[[make_hit(7, "Magic Maze")]],
            reply=_REPLY)
        engine.reply("un gioco cooperativo", session_id="s")
        assert len(engine.last_turn_searches) == 1
        assert "forced" not in engine.last_turn_searches[0]

    def test_forced_search_with_no_hits_still_degrades_honestly(self):
        """The floor searches and finds nothing → the honest no-match is now EARNED."""
        engine, _, _ = make_engine(
            scripted=[AIMessage(content="")],
            hits_batches=[[]],
            reply=_REPLY)
        response = engine.reply("qualcosa che non esiste", session_id="s")
        assert engine.last_turn_searches[0]["n_hits"] == 0
        assert response.games == []
