"""PHASE 1 — Full ingest + DB population, and the scraper stays ON THE RAILS.

Observes the single real ingest (conftest `ingest`, pipeline Curator→Web→Synth→Compose over the
oracle games). This phase doesn't measure quality: it checks the mechanism runs end to end and
that the web stayed under control.

Key points:
  - if the scraper had "left the rails" (an unrecorded query/URL), RailedSearch /
    RailedFetcher would have raised OutOfRailsError DURING the ingest → the session fixture
    would have blown up and all these tests would error. Getting here green IS the proof it stayed
    on the rails.
  - the Web fires ONLY when it should: `expect_web` per game (Onitama/TM stripped: yes;
    Viticulture rich: no). Checks both the firing and the "correctly NOT searching".
"""

import pytest

pytestmark = pytest.mark.e2e


def test_ingest_completed_and_db_populated(ingest):
    """The ingest ran end to end and every game is in the system-of-record (SQLite)."""
    assert ingest.cases, "no e2e case loaded (missing fixtures?)"
    for c in ingest.cases:
        stored = ingest.store.get_game(c.id_product)
        assert stored is not None, f"{c.slug}: not persisted in EnrichmentStore"
        assert stored.embed_text, f"{c.slug}: empty embed_text (Compose produced no text)"


def test_web_fires_only_when_expected(ingest):
    """The scraper fires when info is missing (stripped DTOs) and NOT when the DTO is already rich
    (Viticulture). Checks the WebEnricher's firing guard at the head of the pipeline."""
    for c in ingest.cases:
        fired = c.query in ingest.served_queries
        assert fired == c.expect_web, (
            f"{c.slug}: web_fired={fired} but expect_web={c.expect_web} "
            f"(missing_info after the Curator not as expected)"
        )


def test_no_query_left_the_rails(ingest):
    """Every served web query belongs to the recorded set: nothing left the rails. (An unexpected
    query would already have raised OutOfRailsError during ingest; this is the explicit check.)"""
    known = {c.query for c in ingest.cases}
    extra = [q for q in ingest.served_queries if q not in known]
    assert not extra, f"queries served off the rails: {extra}"


def test_web_pages_cached(ingest):
    """The page cache is populated: the frozen pages are in the DB (web_pages), so no real fetch
    happened during the ingest."""
    for c in ingest.cases:
        for url in c.pages:
            assert ingest.store.get_page(url) is not None, f"{c.slug}: page not cached: {url}"


def test_web_provenance_recorded(ingest):
    """For games where the Web fires, the extractions are tracked with provenance (info, value,
    quote, source domain) in the extractions table."""
    for c in ingest.cases:
        if not c.expect_web:
            continue
        extractions = ingest.store.get_extractions(c.id_product)
        assert extractions, f"{c.slug}: the Web should have fired but recorded no extractions"
        for e in extractions:
            assert e["info"] and e["value"] and e["quote"], f"{c.slug}: incomplete extraction: {e}"
            assert e["source_domain"], f"{c.slug}: extraction without source domain: {e}"
