"""CuratorEnricher — the deterministic CATALOG SHORTCUT for cooperative play (SEL-142).

`_catalog_says_cooperative` lets the curator skip the LLM when the certain data already names the
mode. Checked through the curator's OUTPUT (not as a private predicate): when the catalog names
co-op the verdict is True with NO inference call; when it does not — a brand abbrev, an explicit
negation, competitive flavour — the curator must FALL THROUGH to the inference (here faked to
'incerto' → stays None) instead of fabricating a True from a stray substring.

HOW: fake LLM via `make_curator(content)`; the co-op inference prompt is identifiable by "MODALITÀ".
"""

import json

import pytest

from tests.factories.game import make_game


def _coop(modalita: str) -> str:
    return json.dumps({"modalita": modalita})


def _consulted_inference(curator) -> bool:
    return any("MODALITÀ" in call for call in curator._llm.calls)


class TestCatalogShortcut:
    @pytest.mark.parametrize("certain", [
        {"tags": ["Avventura", "Cooperativo"]},
        {"tags": ["COOPERATIVO"]},               # case-insensitive
        {"tags": ["Cooperativa"]},               # Italian inflections the catalog uses
        {"tags": ["Cooperativi"]},
        {"categoria": "Giochi cooperativi"},     # category, not only tags
        {"tags": ["Non cooperativo", "Cooperativo"]},  # a clean positive next to a negation
    ])
    def test_catalog_signal_shortcuts_to_true_without_inference(self, make_curator, certain):
        # the fake LLM would say the OPPOSITE — proving the shortcut, not the model, decided.
        c = make_curator(_coop("competitivo"))
        out = c.enrich(make_game(description="qualcosa", **certain))
        assert out.enriched.cooperative is True
        assert not _consulted_inference(c)

    @pytest.mark.parametrize("certain", [
        {"tags": ["Coop"]},                              # retailer brand / abbrev, not the mode
        {"tags": ["Gioco non cooperativo"]},             # explicit negation
        {"categoria": "Competitivo, non cooperativo"},
        {"tags": ["Maggioranze", "Piazzamento lavoratori"]},  # Lords of Hellas — competitive
        # Dungeon Saga — one-vs-many: heroes team up against an overlord PLAYER, not a co-op game
        {"tags": ["Combattimento", "Dungeon Crawler"], "categoria": "Giochi di Avventura"},
    ])
    def test_no_catalog_signal_falls_through_to_inference(self, make_curator, certain):
        c = make_curator(_coop("incerto"))  # inference abstains → stays None, no fabricated True
        out = c.enrich(make_game(description="qualcosa", **certain))
        assert out.enriched.cooperative is None
        assert _consulted_inference(c)
