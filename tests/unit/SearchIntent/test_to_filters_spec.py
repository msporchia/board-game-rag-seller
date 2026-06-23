"""SearchIntent.to_filters_spec — the model's proposed constraints → a SearchFilters spec.

Focus: the `cooperative` constraint (SEL-142) is genuine tri-state. The model proposes; the code
disposes — an explicit True/False each become a hard filter (cooperative / competitive), and a
null (no preference) is left out so a non-request never silently constrains the search.
"""

from app.chat.models.intent import SearchIntent


class TestToFiltersSpec:
    def test_cooperative_true_becomes_a_hard_filter(self):
        assert SearchIntent(cooperative=True).to_filters_spec() == {"cooperative": {"val": True}}

    def test_cooperative_false_becomes_a_hard_filter(self):
        assert SearchIntent(cooperative=False).to_filters_spec() == {"cooperative": {"val": False}}

    def test_cooperative_none_is_absent(self):
        assert "cooperative" not in SearchIntent().to_filters_spec()

    def test_coexists_with_other_constraints(self):
        spec = SearchIntent(players=2, cooperative=True).to_filters_spec()
        assert spec == {"players": {"vals": [2]}, "cooperative": {"val": True}}
