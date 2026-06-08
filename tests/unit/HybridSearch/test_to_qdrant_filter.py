"""Purpose: SearchFilters.from_dict builds the right filters, translates them to Qdrant, and
rejects nonsense early.

What it tests: each spec entry maps to the expected Qdrant condition (MatchAny / Range / MatchValue,
with the "metadata." payload prefix), min/max collapse into one Range, soft constraints leave the
hard pre-filter, and the per-filter sanity checks raise on bad input (unknown name, empty/negative
players, out-of-scale complexity, empty range, min>max).

How: no Qdrant server — we inspect the objects built by `SearchFilters.from_dict`.
"""

import pytest
from qdrant_client import models as qm

from app.rag.filters import SearchFilters, UnknownFilterError


def hard(spec):
    return SearchFilters.from_dict(spec).hard_filter()


class TestToQdrantFilter:
    def test_players_is_match_any(self):
        f = hard({"players": {"vals": [2, 3]}})
        assert isinstance(f, qm.Filter) and len(f.must) == 1
        cond = f.must[0]
        assert cond.key == "metadata.players"  # langchain_qdrant nests payload under "metadata"
        assert isinstance(cond.match, qm.MatchAny) and cond.match.any == [2, 3]

    def test_duration_min_max_collapse_into_one_range(self):
        cond = hard({"duration": {"min": 30, "max": 60}}).must[0]
        assert cond.key == "metadata.duration_min"
        assert cond.range.gte == 30 and cond.range.lte == 60

    def test_age_is_upper_bound_on_age_min(self):
        cond = hard({"age": {"max": 8}}).must[0]
        assert cond.key == "metadata.age_min"
        assert cond.range.lte == 8 and cond.range.gte is None

    def test_expansions_is_match_value(self):
        cond = hard({"expansions": {"val": False}}).must[0]
        assert cond.key == "metadata.is_expansion"
        assert isinstance(cond.match, qm.MatchValue) and cond.match.value is False

    def test_fields_are_anded(self):
        f = hard({"players": {"vals": [2]}, "duration": {"max": 60}, "expansions": {"val": False}})
        assert {c.key for c in f.must} == {
            "metadata.players", "metadata.duration_min", "metadata.is_expansion"}

    def test_empty_spec_produces_no_hard_filter(self):
        sf = SearchFilters.from_dict({})
        assert sf.is_empty() and sf.hard_filter() is None

    def test_soft_constraint_leaves_hard_and_moves_to_predicates(self):
        sf = SearchFilters.from_dict({"players": {"vals": [2]}, "duration": {"max": 60, "soft": True}})
        assert [c.key for c in sf.hard_filter().must] == ["metadata.players"]
        preds = sf.soft_predicates()
        assert len(preds) == 1
        assert preds[0]({"duration_min": 50}) is True
        assert preds[0]({"duration_min": 90}) is False

    def test_all_soft_means_no_hard_filter(self):
        sf = SearchFilters.from_dict({"players": {"vals": [2], "soft": True}})
        assert sf.hard_filter() is None and len(sf.soft_predicates()) == 1


class TestSanityChecks:
    def test_unknown_filter_name(self):
        with pytest.raises(UnknownFilterError):
            SearchFilters.from_dict({"nonsense": {"vals": [1]}})

    def test_empty_players(self):
        with pytest.raises(ValueError):
            SearchFilters.from_dict({"players": {"vals": []}})

    def test_non_positive_players(self):
        with pytest.raises(ValueError):
            SearchFilters.from_dict({"players": {"vals": [0, 2]}})

    def test_complexity_out_of_scale(self):
        with pytest.raises(ValueError):
            SearchFilters.from_dict({"complexity": {"max": 9}})

    def test_range_without_bounds(self):
        with pytest.raises(ValueError):
            SearchFilters.from_dict({"duration": {}})

    def test_range_min_greater_than_max(self):
        with pytest.raises(ValueError):
            SearchFilters.from_dict({"duration": {"min": 90, "max": 30}})
