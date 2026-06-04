"""Fixtures LOCAL to the SynthEnricher unit.

`make_synth` builds the enricher with a fake LLM (`FakeLLM` from `tests.factories`) — the tests
are deterministic and never touch Ollama. The `output` is the prose the model "returns" (Synth
emits plain text, not JSON), so it is passed through raw.
"""

import pytest

from app.ingestion.enricher import SynthEnricher
from tests.factories import FakeLLM


@pytest.fixture
def make_synth():
    def _make(output: str = "", **kwargs) -> SynthEnricher:
        enricher = SynthEnricher(**kwargs)
        enricher._llm = FakeLLM(output)
        return enricher

    return _make
