"""Enrichers not yet implemented: they must fail explicitly (NotImplementedError).

When one of these is implemented, promote it to `tests/unit/<ClassName>/`.
"""

import pytest

from app.ingestion.enricher import AugmentEnricher, ExtractEnricher, GapFillEnricher
from tests.factories import make_game


class TestUnimplementedEnrichers:
    @pytest.mark.parametrize("cls", [ExtractEnricher, AugmentEnricher, GapFillEnricher])
    def test_raises_not_implemented(self, cls):
        with pytest.raises(NotImplementedError):
            cls().enrich(make_game())
