"""Two-part model: original (hard-truth) / enriched (working copy)."""

from tests.factories import make_game


class TestGameDoc:
    def test_from_dto_seeds_enriched_equal_to_original(self):
        g = make_game(description="abc", players=[2, 3], tags=["X"])
        assert g.enriched.model_dump() == g.original.model_dump()

    def test_enriched_is_deep_independent_copy(self):
        """Mutating enriched, original (hard-truth) stays intact."""
        g = make_game(players=[2, 3], tags=["X"])
        assert g.enriched.players is not g.original.players  # deep copy, not a shared reference
        g.enriched.players.append(99)
        g.enriched.tags.append("Y")
        assert g.original.players == [2, 3]
        assert g.original.tags == ["X"]

    def test_convenience_properties(self):
        g = make_game(id_product=42, content_hash="h")
        assert g.id_product == 42
        assert g.content_hash == "h"
