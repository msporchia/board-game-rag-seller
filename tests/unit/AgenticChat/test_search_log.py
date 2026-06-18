"""AgenticChat.last_turn_searches — per-tool-call observability (docs/idee.md §Q).

Purpose: the agent records each tool call the model made — {query, filters, n_hits, hit_ids} —
the equivalent of the piloted engine's `turn_searches`. This is what makes tool-use quality
DEBUGGABLE and MEASURABLE: in particular whether the model used the structured constraint fields
(players/duration/age) or stuffed a constraint into free text (a crude, all-text query → empty
`filters`). The first is what we want; the second is the failure the record lets us catch.
"""

from langchain_core.messages import AIMessage

from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply

from tests.unit.AgenticChat.fakes import make_engine, make_hit, tool_call

_GROUNDED = ChatReply(intro="ok", recommendations=[ChatRecommendation(id=1, pitch="A!")])


class TestSearchLog:
    def test_records_structured_filters_when_the_model_uses_them(self):
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "gioco cooperativo", "players": 2}),
                      AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "Pandemic")]],
            reply=_GROUNDED)

        engine.reply("un cooperativo per due", session_id="s1")

        assert engine.last_turn_searches == [{
            "query": "gioco cooperativo",
            "filters": {"players": {"vals": [2]}},   # "per due" became a structured filter
            "n_hits": 1,
            "hit_ids": [1],
        }]

    def test_reveals_a_crude_all_text_query(self):
        # The model stuffed the player count into the free text instead of the `players` field:
        # the record shows it (empty `filters`, the constraint stuck in `query`) so an eval can
        # score it as a crude query.
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "gioco cooperativo per due giocatori"}),
                      AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "Pandemic")]],
            reply=_GROUNDED)

        engine.reply("un cooperativo per due", session_id="s1")

        record = engine.last_turn_searches[0]
        assert record["filters"] == {}                       # no structured constraint used
        assert "per due giocatori" in record["query"]        # it was dumped into free text

    def test_records_every_search_in_a_multi_round_turn(self):
        engine, _, _ = make_engine(
            scripted=[tool_call({"query": "astratto"}, "1"),
                      tool_call({"query": "strategico", "max_minutes": 60}, "2"),
                      AIMessage(content="fatto")],
            hits_batches=[[make_hit(1, "A")], [make_hit(2, "B")]],
            reply=_GROUNDED)

        engine.reply("qualcosa", session_id="s1")

        assert [s["query"] for s in engine.last_turn_searches] == ["astratto", "strategico"]
        assert engine.last_turn_searches[1]["filters"] == {"duration": {"max": 60}}
        assert engine.last_turn_searches[1]["hit_ids"] == [2]
