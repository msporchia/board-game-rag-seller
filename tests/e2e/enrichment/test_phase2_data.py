"""PHASE 2 — The data lands in the RIGHT PLACES (checked against the expected structure).

Observes the same ingest and checks each characteristic is where it belongs, splitting the
DETERMINISTIC part (exactly verifiable) from the ENRICHED part (robust check):

  - `original` stays immutable hard-truth (the pipeline only works on `enriched`);
  - STRUCTURED facts (players, duration, complexity, tags) land in `embed_text` via the
    deterministic RuleComposeEnricher sentences → assertable VERBATIM (the "split" characteristic,
    distributed into the right spots of the text to embed);
  - DESCRIPTIVE extracted facts (setting/theme, genre, audience) land in `extracted` (expected
    keys);
  - Web extractions carry a VERBATIM quote verifiable in the source page (end-to-end
    anti-hallucination).
"""

import pytest

from app.ingestion.enricher import RuleComposeEnricher
from app.models import GameData, GameDoc

pytestmark = pytest.mark.e2e

_RC = RuleComposeEnricher()


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def test_original_is_immutable_hard_truth(ingest):
    """The pipeline doesn't touch `original`: it stays identical to the (stripped) input DTO."""
    for c in ingest.cases:
        doc = ingest.full_docs[c.id_product]
        expected = GameDoc.from_dto(c.ingest_dto()).original
        assert doc.original.model_dump() == expected.model_dump(), (
            f"{c.slug}: original was modified by the pipeline (must stay hard-truth)"
        )


def test_structured_facts_land_in_embed_text(ingest):
    """The certain structured facts appear in embed_text as deterministic Compose sentences —
    exact, because Compose uses no LLM. This is the "split" characteristic in the right places."""
    for c in ingest.cases:
        doc = ingest.full_docs[c.id_product]
        e = doc.enriched
        text = doc.embed_text or ""
        for label, sentence in (
            ("players", _RC._players(e)),
            ("duration", _RC._duration(e)),
            ("complexity", _RC._complexity(e)),
            ("tags", _RC._tags(e)),
        ):
            if sentence:  # only fields present in the DTO
                assert sentence in text, f"{c.slug}: {label!r} sentence missing from embed_text: {sentence!r}"


def test_descriptive_facts_land_in_extracted(ingest):
    """Descriptive info (with no structured field) lands in the `extracted` bag, from Curator
    and/or Web. Robust check: at least the expected taxonomy keys are present."""
    for c in ingest.cases:
        doc = ingest.full_docs[c.id_product]
        keys = set(doc.extracted)
        assert "ambientazione/tema" in keys or "genere" in keys, (
            f"{c.slug}: no descriptive info extracted (extracted={keys})"
        )


def test_web_extractions_are_verbatim(ingest):
    """Every Web-extracted fact quotes the source page VERBATIM (the same anti-hallucination
    guarantee as the WebEnricher, verified end-to-end on the persisted data)."""
    for c in ingest.cases:
        if not c.expect_web:
            continue
        for e in ingest.store.get_extractions(c.id_product):
            page = ingest.store.get_page(e["source_url"])
            assert page is not None, f"{c.slug}: source page not cached: {e['source_url']}"
            assert _norm(e["quote"]) in _norm(page), (
                f"{c.slug}: quote not verbatim in source: {e['quote']!r}"
            )


def test_enriched_keeps_certain_data(ingest):
    """Certain data present in the DTO always wins: the pipeline doesn't overwrite it in `enriched`."""
    for c in ingest.cases:
        doc = ingest.full_docs[c.id_product]
        src = GameData(**c.ingest_dto())
        if src.players:
            assert doc.enriched.players == src.players, f"{c.slug}: players altered"
        if src.duration_min:
            assert doc.enriched.duration_min == src.duration_min, f"{c.slug}: duration altered"
        if src.complexity:
            assert doc.enriched.complexity == src.complexity, f"{c.slug}: complexity altered"
