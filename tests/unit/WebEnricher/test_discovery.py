"""WebEnricher — DISCOVERY (name cleanup + source ranking).

PURPOSE: before querying the LLM, the step must search with the right name and order the
sources by reliability.
WHAT IT TESTS: (a) `_clean_name` removes the marketing attached to the catalog name; (b)
`_ranked` drops blocklisted domains and puts the whitelist first, keeping the unknown ones
(whose seriousness the LLM will decide later).
HOW: pure functions over hand-built `SearchResult`; no network (conftest).
"""

import pytest

from app.core.web_search import SearchResult
from app.ingestion.enricher import WebEnricher


class TestWebEnricherDiscovery:
    @pytest.mark.parametrize("raw,clean", [
        ("Viticulture - Gioco da Tavolo", "Viticulture"),
        ("Onitama – ediz. ITA", "Onitama"),
        ("Dixit | Asmodee", "Dixit"),
        ("Azul", "Azul"),
    ])
    def test_clean_name_strips_marketing(self, raw, clean):
        """The catalog name is cleaned at the marketing separators."""
        assert WebEnricher._clean_name(raw) == clean

    def test_ranked_drops_blocked_and_prioritizes_trusted(self, make_web):
        """Blocklist out, whitelist first, unknown ones kept at the tail."""
        w = make_web()
        w.trusted = {"good.it"}
        w.blocked = {"bad.it"}
        results = [SearchResult(url=f"https://{d}/x")
                   for d in ("unknown.it", "bad.it", "good.it")]
        ranked = [r.domain for r in w._ranked(results)]
        assert "bad.it" not in ranked      # blocklist
        assert ranked[0] == "good.it"       # whitelist first
        assert "unknown.it" in ranked       # unknown kept (the LLM decides later)
