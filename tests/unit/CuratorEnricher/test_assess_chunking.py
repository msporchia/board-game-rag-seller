"""CuratorEnricher — `assess()` chunking: when `needed_labels` exceeds `max_per_call`, the LLM
is called multiple times and the results merged. On production DTOs (all fields present) a SINGLE
call suffices (3 descriptive labels); chunking is for the eval cases with multiple strips.

HOW: fake LLM via `make_curator(payload)` + hand-built games (`make_game`).
"""

from tests.factories.game import make_game


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
