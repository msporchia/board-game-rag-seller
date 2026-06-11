"""Purpose: `SearchFilters.from_dict` rejects nonsense early — the per-filter sanity checks
raise on bad input (unknown name, empty/negative players, out-of-scale complexity, empty
range, min>max).

How: no Qdrant server — validation happens while building the filters.
"""

import pytest

from app.rag.filters.errors import UnknownFilterError
from app.rag.filters.search_filters import SearchFilters


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
