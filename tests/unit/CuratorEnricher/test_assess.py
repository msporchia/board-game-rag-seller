"""CuratorEnricher — `assess()`: dynamic list + verbatim quote validation.

PURPOSE
-------
In the new Curator the LLM does NOT receive the CERTAIN DATA: it reads ONLY the description.
For each label it produces `{citazione, valore_normalizzato}`; `assess()` (a) asks ONLY the
labels that are needed (descriptive always + structured missing in the DTO), (b) chunks into
batches of `max_per_call`, (c) VALIDATES the verbatim quote → degrades if fabricated, (d)
derives `{estratti, presenti, mancanti}` with `presenti` also including the structurally-present
ones (not asked to the LLM).

WHAT IT TESTS
- Canonical contract (3 keys) over 10 real DTOs.
- The prompt sent to the LLM contains a snippet of the real description.
- The LLM is called only on the `needed_labels` (the dynamic list).
- Structured ones already in the DTO go straight to `presenti` (no LLM call needed).
- ANTI-FABRICATION: a fabricated quote (not in the desc) → label in mancanti.

HOW: fake LLM via `make_curator(payload)`. The LOCAL fixture provides 10 real DTOs; the
`per_label(...)` payload simulates the LLM response in the new {citazione, valore_normalizzato} schema.
"""

import json
from pathlib import Path

import pytest

from app.ingestion.sources.json_source import JsonSource
from tests.factories import make_game

FIXTURE = Path(__file__).parent / "fixtures" / "games.json"
_DTOS = json.loads(FIXTURE.read_text(encoding="utf-8"))
GAMES = [JsonSource([d]).fetch()[0] for d in _DTOS]
IDS = [f"{g.original.id_product}-{g.original.name[:24]}" for g in GAMES]


class TestCuratorAssess:
    """Contract + dynamic labels + prompt fidelity over real inputs."""

    @pytest.mark.parametrize("g", GAMES, ids=IDS)
    def test_contract_keys_on_real_game(self, make_curator, per_label, g):
        """Canonical output: ALWAYS the 3 keys {estratti, presenti, mancanti}."""
        a = make_curator(per_label()).assess(g)
        assert set(a) == {"estratti", "presenti", "mancanti"}
        assert isinstance(a["estratti"], dict)
        assert isinstance(a["presenti"], list)
        assert isinstance(a["mancanti"], list)

    @pytest.mark.parametrize("g", GAMES, ids=IDS)
    def test_structurally_present_go_to_presenti(self, make_curator, per_label, g):
        """The structured ones already in the DTO go DIRECTLY into `presenti`, without going
        through the LLM. The core fixture always has all the BGG fields → at least 4 structured
        ones land in presenti for each game (barring edge cases)."""
        a = make_curator(per_label()).assess(g)
        e = g.enriched
        if e.tags:                    assert "meccaniche principali" in a["presenti"]
        if e.players:                 assert "numero giocatori" in a["presenti"]
        if e.duration_min is not None: assert "durata" in a["presenti"]
        if e.complexity:              assert "complessità" in a["presenti"]

    @pytest.mark.parametrize("g", GAMES, ids=IDS)
    def test_prompt_carries_real_description(self, make_curator, per_label, g):
        """The prompt sent to the LLM contains a snippet of the game's real description."""
        desc = (g.original.description or "").strip()
        if not desc:
            pytest.skip(f"game with no description ({g.original.name})")
        c = make_curator(per_label())
        c.assess(g)
        assert c._llm.calls, "assess() did not invoke the LLM"
        head = desc[:80]
        assert any(head in call for call in c._llm.calls), "description not passed in the prompt"

    @pytest.mark.parametrize("g", GAMES, ids=IDS)
    def test_prompt_does_NOT_contain_certain_facts_lines(self, make_curator, per_label, g):
        """The prompt must no longer contain the CERTAIN DATA block: we work only on the desc."""
        c = make_curator(per_label())
        c.assess(g)
        for call in c._llm.calls:
            assert "DATI CERTI" not in call
            assert "Giocatori:" not in call

    @pytest.mark.parametrize("g", GAMES, ids=IDS)
    def test_llm_called_only_on_needed_labels(self, make_curator, per_label, g):
        """The labels in the prompt are ONLY the `needed_labels` (descriptive + missing
        structured), not the whole list of 7."""
        c = make_curator(per_label())
        c.assess(g)
        all_calls = " ".join(c._llm.calls)
        # the structured ones present in the DTO must NOT appear as LABELS in the prompt
        e = g.enriched
        if e.tags:        assert "- meccaniche principali" not in all_calls
        if e.players:     assert "- numero giocatori"      not in all_calls
        if e.duration_min is not None: assert "- durata"   not in all_calls
        if e.complexity:  assert "- complessità"            not in all_calls
        # the descriptive ones are always there
        assert "- ambientazione/tema" in all_calls
        assert "- genere" in all_calls


class TestCuratorAssessValidation:
    """The key INVARIANT: no fabricated quote survives."""

    def test_fabricated_citation_degrades_to_mancanti(self, make_curator, per_label):
        """The LLM quotes "mitologia greca" but the desc doesn't say it → degrade to mancanti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca",
                                    "valore_normalizzato": "greco"},   # FABRICATED
        })
        g = make_game(description="Un gioco generico senza dettagli.")
        a = make_curator(payload).assess(g)
        assert "ambientazione/tema" in a["mancanti"]
        assert "ambientazione/tema" not in a["presenti"]
        assert "ambientazione/tema" not in a["estratti"]

    def test_valid_text_citation_goes_to_presenti_and_estratti(self, make_curator, per_label):
        """VERBATIM quote in the description → present + value in estratti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca",
                                    "valore_normalizzato": "mitologia greca"},
        })
        g = make_game(description="Un gioco di mitologia greca antica.")
        a = make_curator(payload).assess(g)
        assert "ambientazione/tema" in a["presenti"]
        assert a["estratti"]["ambientazione/tema"] == "mitologia greca"

    def test_nessuno_value_goes_to_mancanti(self, make_curator, per_label):
        """`valore_normalizzato: "NESSUNO"` → label in mancanti, nothing in estratti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "", "valore_normalizzato": "NESSUNO"},
        })
        a = make_curator(payload).assess(make_game(description="qualcosa"))
        assert "ambientazione/tema" in a["mancanti"]
        assert "ambientazione/tema" not in a["estratti"]

    def test_fallback_to_citation_when_value_empty(self, make_curator, per_label):
        """If the LLM leaves `valore_normalizzato=""` but quotes a valid passage, we use the
        quote as the value (better something quoted than nothing)."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca", "valore_normalizzato": ""},
        })
        g = make_game(description="Mitologia greca antica.")
        a = make_curator(payload).assess(g)
        assert a["estratti"]["ambientazione/tema"] == "mitologia greca"

    def test_meccaniche_text_value_is_split_into_list(self, make_curator, per_label):
        """For 'meccaniche principali' the extracted string becomes a LIST."""
        payload = per_label(**{
            "meccaniche principali": {"citazione": "cooperativo, lancio di dadi",
                                       "valore_normalizzato": "Cooperativo, Lancio di dadi"},
        })
        g = make_game(description="cooperativo, lancio di dadi", tags=[])
        a = make_curator(payload).assess(g)
        assert a["estratti"]["meccaniche principali"] == ["Cooperativo", "Lancio di dadi"]


class TestCuratorChunking:
    """When `needed_labels` exceeds `max_per_call`, the LLM is called multiple times and the
    results merged. On production DTOs (all fields present) a SINGLE call suffices (3 descriptive
    labels); chunking is for the eval cases with multiple strips."""

    def test_one_call_when_few_labels(self, make_curator, per_label):
        """Complete DTO → 3 labels → a single call (≤ max_per_call=4)."""
        g = make_game(tags=["X"], players=[2], duration_min=60, complexity="Medio")
        c = make_curator(per_label())
        c.assess(g)
        assert len(c._llm.calls) == 1

    def test_chunked_calls_when_many_labels(self, make_curator, per_label):
        """Fully bare DTO (no struct) → 7 needed → max_per_call=4 → 2 batches."""
        g = make_game(tags=[], players=[], duration_min=None, complexity=None,
                      description="qualcosa")
        c = make_curator(per_label(), max_per_call=4)
        c.assess(g)
        assert len(c._llm.calls) == 2  # 4 + 3
