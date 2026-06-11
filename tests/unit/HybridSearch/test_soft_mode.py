"""Purpose: SOFT constraints (soft=True) promote matching games but never exclude.

What it tests:
- `rerank_soft` (pure): a satisfied soft predicate boosts the score enough to overtake a
  higher-ranked non-match; non-matching points (incl. those missing the field) keep their score
  and stay in the list (no drop).
- End-to-end via in-memory Qdrant: the SAME constraint as hard excludes, as soft keeps the whole
  corpus — that is the hard/soft contract.

How: the pure part builds (doc, score) tuples directly (no embedding needed); the integration
part reuses the conftest store.
"""

from app.rag.filters.rerank import SOFT_BOOST, rerank_soft
from app.rag.filters.search_filters import SearchFilters


def players_predicate(vals):
    return SearchFilters.from_dict({"players": {"vals": vals, "soft": True}}).soft_predicates()[0]


class _Doc:
    def __init__(self, metadata):
        self.metadata = metadata


class TestRerankSoftPure:
    def test_boost_overtakes_higher_nonmatch(self):
        a = (_Doc({"players": [4]}), 0.50)        # no match, higher base score
        b = (_Doc({"players": [2]}), 0.49)        # match, lower base score
        pred = players_predicate([2])
        # sanity: a single boost is enough here (0.49 * 1.1 = 0.539 > 0.50)
        assert 0.49 * (1 + SOFT_BOOST) > 0.50
        ranked = rerank_soft([a, b], [pred])
        assert [d.metadata["players"] for d, _ in ranked] == [[2], [4]]

    def test_nonmatch_and_missing_are_kept_not_dropped(self):
        items = [(_Doc({"players": [2]}), 0.9),
                 (_Doc({"players": [5]}), 0.8),    # non-match
                 (_Doc({}), 0.7)]                  # missing field
        ranked = rerank_soft(items, [players_predicate([2])])
        assert len(ranked) == 3  # nothing dropped

    def test_no_predicates_is_identity(self):
        items = [(_Doc({"x": 1}), 0.5), (_Doc({"x": 2}), 0.4)]
        assert rerank_soft(items, []) == items


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
