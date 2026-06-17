"""PromoteCooperative — the fetch-intercepting retrieval policy (docs/idee.md §O).

Purpose: lock its concrete, OBSERVABLE effect on the hits — it biases the query toward
cooperative games and brings the cooperative hits to the front (stable). The effect lives
entirely on the retrieval result, independent of any generation prompt: this test stays green
even if the persona/strategy prompts change (the stability the design is for).
"""

from app.chat.policies.policy_set import PolicySet
from app.chat.policies.retrieval_context import RetrievalContext

from tests.unit.PromoteCooperative.fakes import FakeRetriever, make_hit


def _run(hits):
    retriever = FakeRetriever(hits)
    ctx = RetrievalContext(query="qualcosa di carino", k=10, retriever=retriever)
    out = PolicySet.from_names(["promote_cooperative"]).run_retrieve(ctx, lambda c: c.execute())
    return out, retriever


class TestPromoteCooperative:
    def test_cooperative_hits_move_to_the_front_stably(self):
        hits = [make_hit(1, "Solo", categoria="Strategico"),
                make_hit(2, "CoopTag", tags=["Cooperativo"]),
                make_hit(3, "Filler", categoria="Party"),
                make_hit(4, "CoopCat", categoria="Cooperativo")]

        out, _ = _run(hits)

        # Co-op first (ids 2, 4), original order kept within each group; non-co-op after (1, 3).
        assert [h.id_product for h in out] == [2, 4, 1, 3]

    def test_query_is_biased_toward_cooperative_before_the_fetch(self):
        _, retriever = _run([])

        assert "cooperativo" in retriever.calls[0][0].lower()

    def test_no_cooperative_hits_keeps_original_order(self):
        hits = [make_hit(1, "A", categoria="Strategico"), make_hit(2, "B", categoria="Party")]

        out, _ = _run(hits)

        assert [h.id_product for h in out] == [1, 2]
