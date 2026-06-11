"""Shared support for the deterministic WebEnricher tests.

Builds a WebEnricher with a fake LLM (`FakeLLM`) and an inert search (`fakes.NoSearch`): this
way the tests never touch the network and the model output is predictable, leaving only the
step's LOGIC under examination (guard, ranking, quote validation).
"""

import pytest

from app.ingestion.enricher.web import WebEnricher
from tests.factories.llm import FakeLLM
from tests.unit.WebEnricher.fakes import NoSearch


@pytest.fixture
def make_web():
    """Factory: WebEnricher with `FakeLLM(content)` and an inert search (no network)."""

    def _make(content: str = "") -> WebEnricher:
        w = WebEnricher(search=NoSearch(), store=None)
        w._llm = FakeLLM(content)
        return w

    return _make
