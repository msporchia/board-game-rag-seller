"""Enrichers not yet implemented: they must fail explicitly (NotImplementedError).

When one of these is implemented, promote it to `tests/unit/<ClassName>/`.
"""

import pytest

from app.ingestion.enricher.augment import AugmentEnricher
from app.ingestion.enricher.extract import ExtractEnricher
from app.ingestion.enricher.gapfill import GapFillEnricher
from tests.factories import make_game


class TestUnimplementedEnrichers:
    @pytest.mark.parametrize("cls", [ExtractEnricher, AugmentEnricher, GapFillEnricher])
    def test_raises_not_implemented(self, cls):
        with pytest.raises(NotImplementedError):
            cls().enrich(make_game())
