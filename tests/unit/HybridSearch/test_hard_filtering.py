"""Purpose: the HARD pre-filter keeps exactly the right games (and drops the rest), against a
real in-memory Qdrant.

What it tests: exact `players` match (OR inside the field), numeric ranges (duration, complexity),
`expansions`, the AND between fields, and the MISSING-FIELD rule — a game without the filtered
field (Delta has no duration/complexity) is excluded by a hard range on it.

How: index the known corpus (conftest) into in-memory Qdrant, run the retriever with a filter spec,
assert the returned id set. Order is irrelevant here (the filter excludes; the ranking is semantic),
so we compare sets. The query text is a fixed dummy — only the filter decides membership.
"""

from app.rag.filters.search_filters import SearchFilters

Q = "gioco"  # dummy semantic query; the filter is what we assert


def ids(retriever, spec) -> set[int]:
    hits = retriever.search(Q, k=10, filters=SearchFilters.from_dict(spec))
    return {h.id_product for h in hits}


class TestHardFiltering:
    def test_players_or_match(self, retriever):
        # games whose exploded players list contains 2: Alpha, Bravo, Delta, Foxtrot
        assert ids(retriever, {"players": {"vals": [2]}}) == {1, 2, 4, 6}

    def test_players_multiple_values_is_or(self, retriever):
        # contains 2 OR 5: adds Charlie (has 5) to the set above
        assert ids(retriever, {"players": {"vals": [2, 5]}}) == {1, 2, 3, 4, 6}

    def test_max_duration_range(self, retriever):
        # duration_min <= 60: Alpha(30), Bravo(60), Echo(45). Delta(None) excluded.
        assert ids(retriever, {"duration": {"max": 60}}) == {1, 2, 5}

    def test_max_complexity_range(self, retriever):
        # complexity_level <= 2: Alpha(2), Echo(1). Delta(None) excluded.
        assert ids(retriever, {"complexity": {"max": 2}}) == {1, 5}

    def test_exclude_expansions(self, retriever):
        # Echo is the only expansion → keep is_expansion == False
        assert ids(retriever, {"expansions": {"val": False}}) == {1, 2, 3, 4, 6}

    def test_cooperative_only(self, retriever):
        # cooperative == True: Bravo, Delta. Alpha (False) and the UNKNOWN ones are excluded.
        assert ids(retriever, {"cooperative": {"val": True}}) == {2, 4}

    def test_competitive_only(self, retriever):
        # cooperative == False: Alpha. The co-op (2,4) and UNKNOWN ones are excluded — the flag is
        # genuine tri-state, so a competitive request narrows just as precisely (SEL-142).
        assert ids(retriever, {"cooperative": {"val": False}}) == {1}

    def test_and_between_fields(self, retriever):
        # players contains 2 AND duration_min <= 60: Alpha, Bravo. Foxtrot(90) and Delta(None) out.
        assert ids(retriever, {"players": {"vals": [2]}, "duration": {"max": 60}}) == {1, 2}

    def test_missing_field_excluded_by_hard_range(self, retriever):
        # Delta has duration_min=None → any hard duration constraint must exclude it
        assert 4 not in ids(retriever, {"duration": {"max": 200}})

    def test_no_filter_returns_everything(self, retriever):
        assert ids(retriever, {}) == {1, 2, 3, 4, 5, 6}
