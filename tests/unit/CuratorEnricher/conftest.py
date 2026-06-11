"""Fixtures LOCAL to the CuratorEnricher unit: what is specific to this step lives here.

`make_curator` builds the enricher with a fake LLM (`FakeLLM` from `tests.factories`) — the
tests are deterministic and never touch Ollama. The `payload` simulates the model's response:
a dict is serialized to valid JSON; a string is passed raw (to test the failed-parse path).

`per_label` is the helper to build the "citation-based" payload of the new prompt: by default
each label is {dove: NESSUNO}; passing some as kwargs overrides them.
"""

import json

import pytest

from app.ingestion.enricher.curator import CuratorEnricher
from tests.factories.llm import FakeLLM


@pytest.fixture
def make_curator():
    def _make(payload=None, **kwargs) -> CuratorEnricher:
        enricher = CuratorEnricher(**kwargs)
        content = payload if isinstance(payload, str) else json.dumps(payload or {})
        enricher._llm = FakeLLM(content)
        return enricher

    return _make


@pytest.fixture
def per_label():
    """Builds the per-label dict the LLM produces: default all NESSUNO; the test overrides only
    the labels it wants to drive. E.g.:

        per_label(**{"ambientazione/tema": {"citazione": "mitologia greca",
                                             "valore_normalizzato": "mitologia greca"}})

    The Curator no longer passes the CERTAIN DATA to the LLM: the response schema is only
    `{citazione, valore_normalizzato}` per label.
    """

    def _build(**overrides) -> dict:
        base = {label: {"citazione": "", "valore_normalizzato": "NESSUNO"}
                for label in CuratorEnricher.REQUIRED_INFO}
        base.update(overrides)
        return base

    return _build
