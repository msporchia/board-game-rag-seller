"""SearchCatalogTool.as_tool — the bindable LLM tool surface (docs/idee.md §Q).

Purpose: `as_tool()` exposes a StructuredTool with the right name and args schema (so the strong
model can `bind_tools` it), and invoking it runs the same catalog search. The search logic itself
lives in `test_run.py`.
"""

from app.chat.models.intent import SearchIntent
from app.chat.tools.search_catalog import SearchCatalogTool

from tests.unit.SearchCatalogTool.fakes import FakeRetriever, make_hit


class TestAsTool:
    def test_exposes_a_bindable_structured_tool(self):
        retriever = FakeRetriever([make_hit(7, "Pandemic")])
        st = SearchCatalogTool(retriever=retriever, k=5).as_tool()

        assert st.name == "search_catalog"
        assert st.args_schema is SearchIntent

        out = st.invoke({"query": "cooperativo"})
        assert [h.id_product for h in out] == [7]
