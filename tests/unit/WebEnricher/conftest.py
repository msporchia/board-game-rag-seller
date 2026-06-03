"""Shared support for the deterministic WebEnricher tests.

Builds a WebEnricher with a fake LLM (`FakeLLM`) and an inert search (`NoSearch`): this way the
tests never touch the network and the model output is predictable, leaving only the step's
LOGIC under examination (guard, ranking, quote validation).
"""

import pytest

from app.ingestion.enricher import WebEnricher
from tests.factories import FakeLLM


class NoSearch:
    """Inert search provider: no network call in the deterministic tests."""

    def search(self, *args, **kwargs):
        return []


@pytest.fixture
def make_web():
    """Factory: WebEnricher with `FakeLLM(content)` and an inert search (no network)."""

    def _make(content: str = "") -> WebEnricher:
        w = WebEnricher(search=NoSearch(), store=None)
        w._llm = FakeLLM(content)
        return w

    return _make
