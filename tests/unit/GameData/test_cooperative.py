"""GameData — the `cooperative` field is plain tri-state STORAGE (SEL-142).

The model holds the value; it does not decide it. The verdict (True/False/None) is produced by
the curator (catalog shortcut + LLM inference) and verified against the oracle there
(tests/unit/CuratorEnricher/test_cooperative.py) — not on this pure data model.
"""

from app.models.game_data import GameData


def _game(**overrides) -> GameData:
    return GameData(**{"id_product": 1, "name": "X", **overrides})


class TestGameDataCooperative:
    def test_field_defaults_to_unknown(self):
        assert _game().cooperative is None

    def test_field_stores_explicit_values(self):
        assert _game(cooperative=True).cooperative is True
        assert _game(cooperative=False).cooperative is False

    def test_construction_does_not_auto_derive_from_tag(self):
        # the model infers nothing: a co-op tag is a SHORTCUT for the curator, not an automatic
        # field value — the determination is the curator's job, not the data model's.
        assert _game(tags=["Cooperativo"]).cooperative is None
