"""GameData — the `cooperative` field and its certain-data shortcut (SEL-142).

The field is plain tri-state storage (True/False/None); the VALUE is decided by the curator
(LLM inference). What lives on the model is only `mentions_cooperative()`: the reliable POSITIVE
shortcut over the catalog tags/category that lets the curator skip the inference when the catalog
already states it. Absence proves nothing, so the helper never reports False.
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
        # the model no longer infers anything: a co-op tag is a SHORTCUT for the curator, not an
        # automatic field value — the determination is the curator's inference job.
        assert _game(tags=["Cooperativo"]).cooperative is None

    def test_mentions_cooperative_detects_tag_and_category(self):
        assert _game(tags=["Avventura", "Cooperativo"]).mentions_cooperative() is True
        assert _game(categoria="Giochi cooperativi").mentions_cooperative() is True
        assert _game(tags=["COOPERATIVO"]).mentions_cooperative() is True

    def test_mentions_cooperative_is_false_without_the_stem(self):
        assert _game(tags=["Strategico"], categoria="Strategici").mentions_cooperative() is False
        # "Coop" (a brand/abbrev) must not match — we look for the stem 'cooperativ' on a boundary
        assert _game(tags=["Coop"]).mentions_cooperative() is False

    def test_mentions_cooperative_rejects_explicit_negation(self):
        # an explicit "non cooperativo" tag is a NEGATIVE signal, not a positive one
        assert _game(tags=["Non cooperativo"]).mentions_cooperative() is False
        # a negation in one field must not poison a clean positive in another
        assert _game(tags=["Non cooperativo", "Cooperativo"]).mentions_cooperative() is True

    # --- edge cases, grounded in real catalog games (co-op status verified online) ---

    def test_mentions_cooperative_covers_italian_inflections(self):
        # the stem 'cooperativ' must catch every inflection the catalog actually uses
        for tag in ["Cooperativa", "Cooperativi", "Cooperative", "gioco cooperativo"]:
            assert _game(tags=[tag]).mentions_cooperative() is True, tag

    def test_one_vs_many_overlord_game_is_not_a_catalog_signal(self):
        # Dungeon Saga: Dwarf King's Quest is ONE-VS-MANY — heroes cooperate against an overlord
        # PLAYER, so it is NOT a co-op game and the catalog carries no co-op tag. Dungeon-crawler
        # flavour must not become a deterministic positive (the inference may still decide).
        assert _game(tags=["Combattimento", "Esplorazione", "Fantasy", "Dungeon Crawler"],
                     categoria="Giochi di Avventura").mentions_cooperative() is False

    def test_real_competitive_game_has_no_signal(self):
        # Lords of Hellas — purely competitive area control: nothing in the certain data names co-op.
        assert _game(tags=["Maggioranze", "Piazzamento lavoratori"],
                     categoria="Giochi Gestionali").mentions_cooperative() is False
