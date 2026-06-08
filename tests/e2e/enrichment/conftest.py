"""Shared, SESSION-SCOPED ingest for the enrichment e2e phases.

The real pipeline (LLM + embeddings) is slow, so we pay it once: this fixture runs the whole
ingest a single time (`EnrichmentHarness`) and the phases read the same `RunResult`; the
`Scorecard` derives the metrics from it. Throwaway stores (tmp SQLite + tmp Qdrant collections)
are torn down at the end.

Needs the containers (Ollama + Qdrant) and is NOT part of the offline unit run (pytest.ini
testpaths = tests/unit). Run it explicitly:

    docker exec seller-api python -m pytest tests/e2e/enrichment -v
"""

import pytest

from tests.e2e.enrichment.harness import EnrichmentHarness
from tests.e2e.enrichment.scorecard import Scorecard

COLLECTION_FULL = "e2e_enrichment_full"
COLLECTION_BASE = "e2e_enrichment_base"


@pytest.fixture(scope="session")
def ingest(tmp_path_factory):
    db = tmp_path_factory.mktemp("e2e") / "seller_e2e.db"
    result = EnrichmentHarness(str(db), COLLECTION_FULL, COLLECTION_BASE).run()
    yield result
    result.close()


@pytest.fixture(scope="session")
def scorecard(ingest) -> Scorecard:
    return Scorecard.from_result(ingest)
