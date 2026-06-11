"""RuleComposeEnricher: DETERMINISTIC compose → `embed_text` (Italian output, asserted as-is)."""

import pytest

from app.ingestion.enricher.compose import RuleComposeEnricher
from tests.factories import make_game


class TestRuleComposeEnricher:
    def test_starts_with_name(self):
        out = RuleComposeEnricher().enrich(make_game(name="Avel"))
        assert out.embed_text.startswith("Avel")

    def test_solo_phrasing(self):
        out = RuleComposeEnricher().enrich(make_game(players=[1, 2, 3, 4]))
        assert "Si gioca da 1 a 4 giocatori" in out.embed_text
        assert "giocabile in solitario" in out.embed_text

    def test_two_players_phrasing(self):
        out = RuleComposeEnricher().enrich(make_game(players=[2]))
        assert "Si gioca in 2 giocatori" in out.embed_text
        assert "ottimo in due" in out.embed_text

    @pytest.mark.parametrize("minutes,expected", [
        (20, "breve e veloce"),
        (45, "circa un'ora"),
        (90, "medio-lunga"),
        (150, "lunga e impegnativa"),
    ])
    def test_duration_buckets(self, minutes, expected):
        out = RuleComposeEnricher().enrich(make_game(duration_min=minutes))
        assert expected in out.embed_text

    @pytest.mark.parametrize("level,expected", [
        (2, "principianti"),
        (3, "intermedia"),
        (4, "esperti"),
    ])
    def test_complexity_hint(self, level, expected):
        out = RuleComposeEnricher().enrich(make_game(complexity="Medio", complexity_level=level))
        assert expected in out.embed_text

    def test_tags_line(self):
        out = RuleComposeEnricher().enrich(make_game(tags=["Cooperativo", "Fantasy"]))
        assert "Meccaniche e temi: Cooperativo, Fantasy." in out.embed_text

    def test_does_not_touch_original(self):
        out = RuleComposeEnricher().enrich(make_game(description="orig", players=[2]))
        assert out.original.description == "orig"
