"""WebEnricher — GUARD (online fallback only when needed).

PURPOSE: the WebEnricher is an expensive fallback (network + LLM) and must stay inert when
there is nothing to complete.
WHAT IT TESTS: with no `missing_info` the step is a no-op and triggers neither search nor LLM
(returns the exact same input object).
HOW: a GameDoc with no `missing_info`, a fake LLM and an inert search (see conftest).
"""

from tests.factories.game import make_game


class TestWebEnricherGuard:
    def test_skips_when_no_missing_info(self, make_web):
        """empty missing_info → returns the same object, no network/LLM."""
        g = make_game()  # missing_info empty by default
        assert make_web().enrich(g) is g
