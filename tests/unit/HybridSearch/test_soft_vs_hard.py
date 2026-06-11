"""Purpose: the hard/soft contract end-to-end via in-memory Qdrant — the SAME constraint as
hard excludes, as soft keeps the whole corpus.

How: reuses the conftest store/retriever.
"""

from app.rag.filters.search_filters import SearchFilters


class TestSoftVsHardEndToEnd:
    def test_hard_excludes_soft_keeps(self, retriever):
        # players=[2] as HARD → only the games that support 2 players
        hard = {h.id_product for h in retriever.search(
            "gioco", k=10, filters=SearchFilters.from_dict({"players": {"vals": [2]}}))}
        assert hard == {1, 2, 4, 6}

        # SAME constraint as SOFT → nothing excluded, the whole corpus comes back
        soft = {h.id_product for h in retriever.search(
            "gioco", k=10, filters=SearchFilters.from_dict({"players": {"vals": [2], "soft": True}}))}
        assert soft == {1, 2, 3, 4, 5, 6}
