"""CuratorEnricher — PURE prompt-building functions + helpers.

PURPOSE: the prompt is the Curator's lever; its parts must be verified deterministically.
WHAT IT TESTS:
  - `_prompt`: no CERTAIN DATA, only DESCRIPTION; `{citazione, valore_normalizzato}` schema;
    contains EXACTLY the passed labels (dynamic list).
  - `_certain_facts` / `_collect_descriptions`: pure functions still here (they'll be used by
    the downstream `SynthEnricher`, over combined + multi-source material).
  - `_str_list`: list-robustness helper.
HOW: direct method calls (no LLM).
"""

from app.ingestion.enricher.curator import CuratorEnricher
from tests.factories.game import make_game


class TestCuratorPromptBuilders:
    def test_prompt_is_description_only_citation_based(self, make_curator):
        """The reduced prompt: no CERTAIN DATA, only DESCRIPTION. The LLM produces
        `{citazione, valore_normalizzato}` per label. The VERBATIM quote stays the
        anti-fabrication invariant, validated downstream by the code."""
        labels = ["ambientazione/tema", "genere", "a chi è adatto"]
        prompt = CuratorEnricher._prompt(labels, "una descrizione di prova")
        assert "ETICHETTE" in prompt
        assert "VERBATIM" in prompt
        assert "DESCRIZIONE" in prompt
        # 2-field per-label schema (no more "dove")
        assert "citazione" in prompt
        assert "valore_normalizzato" in prompt
        # no CERTAIN DATA in the prompt
        assert "DATI CERTI" not in prompt and "DATI_CERTI" not in prompt
        assert "Giocatori:" not in prompt
        # no synthesis here
        assert "SINTESI" not in prompt
        assert "\"sintesi\"" not in prompt
        # only the passed labels are in the prompt (dynamic list)
        for lab in labels:
            assert f"- {lab}" in prompt
        assert "- numero giocatori" not in prompt

    def test_certain_facts_lists_present_fields(self, make_curator):
        """Pure function kept in the Curator (the SynthEnricher will use it over combined material)."""
        g = make_game(players=[2, 3, 4], players_display="2-4", duration_min=60,
                      complexity="Medio", tags=["Coop"], categoria="GdT", year=2018)
        facts = make_curator({})._certain_facts(g.enriched)
        assert "Giocatori: 2-4" in facts
        assert "Durata: 60 minuti" in facts
        assert "Meccaniche/temi: Coop" in facts
        assert "Anno: 2018" in facts

    def test_certain_facts_empty(self, make_curator):
        """No structured field → placeholder '(nessuno)'."""
        assert make_curator({})._certain_facts(make_game().enriched) == "(nessuno)"

    def test_collect_descriptions_dedup_and_labels(self, make_curator):
        """Sources labeled, order main→sources, duplicates dropped."""
        g = make_game(description="principale", source_descriptions=[
            {"source": "BGG", "description": "da bgg"},
            {"source": "dup", "description": "principale"},   # duplicate of the main one
            {"source": "Editore", "description": "da editore"},
        ])
        text = make_curator({})._collect_descriptions(g)
        assert text.index("[Descrizione principale]") < text.index("[Fonte: BGG]")
        assert "da editore" in text
        assert "[Fonte: dup]" not in text  # duplicate source-block not added

    def test_str_list_static(self):
        """Static helper: keeps only the strings."""
        assert CuratorEnricher._str_list(["a", 1, None, "b"]) == ["a", "b"]
        assert CuratorEnricher._str_list(None) == []
