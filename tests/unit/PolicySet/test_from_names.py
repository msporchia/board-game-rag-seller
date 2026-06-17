"""PolicySet.from_names — name resolution (docs/idee.md §O).

Purpose: known names resolve in order; unknown names are SKIPPED, not raised (a caller typo must
not 500 a customer turn — unlike SearchFilters, whose names come from a validated model).
"""

from app.chat.policies.policy_set import PolicySet


class TestFromNames:
    def test_resolves_known_names_in_order(self):
        ps = PolicySet.from_names(["christmas_sale", "promote_cooperative"])
        assert ps.names == ["christmas_sale", "promote_cooperative"]

    def test_unknown_names_are_skipped_not_raised(self):
        ps = PolicySet.from_names(["christmas_sale", "does_not_exist"])
        assert ps.names == ["christmas_sale"]
        assert PolicySet.from_names(["nope"]).is_empty()

    def test_none_and_empty_are_empty(self):
        assert PolicySet.from_names(None).is_empty()
        assert PolicySet.from_names([]).is_empty()
