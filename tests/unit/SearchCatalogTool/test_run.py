"""SearchCatalogTool.run — the catalog search the model's tool call triggers (docs/idee.md §Q).

Purpose: declared constraints become real SearchFilters on the search (reusing SearchIntent's
mapping), the query reaches the retriever, `k` is engine-controlled (not a model arg), and every
search is recorded in `calls` (the union feeds grounding / eval). The bindable-tool surface lives
in `test_as_tool.py`.
"""

from app.chat.models.intent import SearchIntent
from app.chat.tools.search_catalog import SearchCatalogTool

from tests.unit.SearchCatalogTool.fakes import FakeRetriever, make_hit


class TestRun:
    def test_constraints_become_filters_and_query_reaches_retriever(self):
        retriever = FakeRetriever([make_hit(1, "A"), make_hit(2, "B")])
        tool = SearchCatalogTool(retriever=retriever, k=3)

        out = tool.run(query="party game", players=6, max_minutes=45)

        query, k, filters = retriever.calls[0]
        assert query == "party game"
        assert k == 3                      # engine-controlled, not a model argument
        assert filters is not None         # a real SearchFilters was built from the constraints
        assert [h.id_product for h in out] == [1, 2]

    def test_records_every_search(self):
        tool = SearchCatalogTool(retriever=FakeRetriever([]), k=5)

        tool.run(query="cooperativo")
        tool.run(query="strategico", players=2)

        assert [c.query for c in tool.calls] == ["cooperativo", "strategico"]
        assert isinstance(tool.calls[0], SearchIntent)

    def test_no_constraints_means_no_filters(self):
        retriever = FakeRetriever([make_hit(1, "A")])
        tool = SearchCatalogTool(retriever=retriever, k=5)

        tool.run(query="qualcosa di bello")

        assert retriever.calls[0][2] is None

    def test_unwraps_a_dict_wrapped_int_arg(self):
        # The model sometimes nests the number (qwen2.5 emitted max_minutes={"max": 180}).
        retriever = FakeRetriever([make_hit(1, "A")])
        tool = SearchCatalogTool(retriever=retriever, k=5)

        tool.run(query="gestionale lungo", max_minutes={"max": 180})

        assert tool.calls[-1].max_minutes == 180
        assert retriever.calls[0][2] is not None  # the coerced constraint became a real filter

    def test_drops_uncoercible_constraints_instead_of_raising(self):
        retriever = FakeRetriever([make_hit(1, "A")])
        tool = SearchCatalogTool(retriever=retriever, k=5)

        tool.run(query="x", players="tanti", max_minutes={})  # neither coerces to an int

        assert tool.calls[-1].players is None and tool.calls[-1].max_minutes is None
        assert retriever.calls[0][2] is None  # no filters — the bad args were dropped, not raised
