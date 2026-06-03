"""Fixture LOCAL to the EnrichmentStore unit: store on in-memory SQLite.

Isolated per test (no file on disk, no shared state): each test gets a freshly created store
and closes it at the end.
"""

import pytest

from app.core.enrichment_store import EnrichmentStore


@pytest.fixture
def store():
    s = EnrichmentStore(path=":memory:")
    yield s
    s.close()
