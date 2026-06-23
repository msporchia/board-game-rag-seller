"""PROMPT QUALITY — does the curator's cooperative inference actually deduce the mode from a real
description? (SEL-142)

The unit tests prove the WIRING with a fake LLM; this one proves the PROMPT. For real corpus
games with a KNOWN play mode (the oracle, verified against BoardGameGeek), we STRIP the catalog
co-op signal so the deterministic shortcut can't fire, then run the REAL CuratorEnricher: the
verdict must come from the description alone.

  - cooperative games  → the inference must RECOVER True (this is "hide the tag, deduce it");
  - competitive games  → it must NEVER fabricate a co-op (False or, at worst, the honest None).

Real LLM, no network beyond Ollama (the curator reads only the description — no Web step here).
Run explicitly: `docker exec seller-api python -m pytest tests/e2e/enrichment/test_cooperative_inference.py -v`
"""

import pytest

from app.ingestion.enricher.curator import CuratorEnricher
from app.models.game_doc import GameDoc
from tests.e2e.enrichment.cases import load_corpus

pytestmark = pytest.mark.e2e

# The oracle: real corpus games with their true play mode (cooperative = True / competitive = False).
# Cooperative picks have unambiguous co-op descriptions ("si gioca tutti insieme contro il gioco");
# the competitive picks are clearly head-to-head — both verified against BoardGameGeek.
ORACLE = {
    1: True,    # Massive Darkness — co-op dungeon crawler
    3: True,    # Pandemic — the canonical co-op
    4: True,    # Le Case della Follia (Mansions of Madness 2nd ed.) — app-driven, fully co-op
    10: True,   # First Martians — co-op survival
    11: True,   # Fireteam Zero — co-op horror
    2: False,   # Lords of Hellas — competitive area control
    7: False,   # Specie Dominanti — competitive
    160: False,  # Onitama — competitive abstract duel
    36: False,  # Puerto Rico — competitive
    34: False,  # Carcassonne — competitive
}


def _doc_without_coop_signal(dto: dict) -> GameDoc:
    """The corpus DTO with the catalog co-op signal removed (tag + any co-op in the category), so
    `_catalog_says_cooperative` cannot fire and only the description can decide. Description kept."""
    stripped = dict(dto)
    stripped["tags"] = [t for t in dto.get("tags", []) if "cooperativ" not in t.lower()]
    if "cooperativ" in (dto.get("categoria") or "").lower():
        stripped["categoria"] = ""
    return GameDoc.from_dto(stripped)


@pytest.fixture(scope="module")
def corpus() -> dict:
    return load_corpus()


@pytest.mark.parametrize("id_product,expected", list(ORACLE.items()))
def test_cooperative_is_deduced_from_description(corpus, id_product, expected):
    dto = corpus[id_product]
    doc = _doc_without_coop_signal(dto)
    assert doc.enriched.cooperative is None  # signal stripped → no shortcut, must infer

    out = CuratorEnricher().enrich(doc)
    verdict = out.enriched.cooperative

    if expected is True:
        # the whole point: the prompt RECOVERS co-op from the description with the tag hidden
        assert verdict is True, f"{dto['name'][:40]!r}: co-op not deduced (got {verdict})"
    else:
        # a competitive game must never be mislabelled cooperative (None = honest abstain, allowed)
        assert verdict is not True, f"{dto['name'][:40]!r}: fabricated co-op (got {verdict})"
