"""CuratorEnricher — `assess()`: contract + dynamic labels + prompt fidelity over real inputs.

PURPOSE
-------
In the new Curator the LLM does NOT receive the CERTAIN DATA: it reads ONLY the description.
For each label it produces `{citazione, valore_normalizzato}`; `assess()` asks ONLY the labels
that are needed (descriptive always + structured missing in the DTO) and derives
`{estratti, presenti, mancanti}` with `presenti` also including the structurally-present ones
(not asked to the LLM). Quote validation and chunking are covered by the sibling files
`test_assess_validation.py` / `test_assess_chunking.py`.

WHAT IT TESTS
- Canonical contract (3 keys) over 10 real DTOs.
- The prompt sent to the LLM contains a snippet of the real description.
- The LLM is called only on the `needed_labels` (the dynamic list).
- Structured ones already in the DTO go straight to `presenti` (no LLM call needed).

HOW: fake LLM via `make_curator(payload)`. The LOCAL fixture provides 10 real DTOs; the
`per_label(...)` payload simulates the LLM response in the new {citazione, valore_normalizzato} schema.
"""

import json
from pathlib import Path

import pytest

from app.ingestion.sources.json_source import JsonSource

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
