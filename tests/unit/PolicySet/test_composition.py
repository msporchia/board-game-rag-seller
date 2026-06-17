"""PolicySet.run_retrieve/run_generate — middleware composition (docs/idee.md §O).

Purpose: the policies compose as an ONION — the first policy is the outermost layer, wrapping
the rest and the stage's real work; an empty set runs the stage unchanged.
"""

from app.chat.policies.policy import Policy
from app.chat.policies.policy_set import PolicySet


class TestComposition:
    def test_first_policy_is_the_outermost_onion_layer(self):
        order: list[str] = []

        class A(Policy):
            name, description = "a", "a"

            def around_retrieve(self, ctx, call_next):
                order.append("enter a")
                result = call_next(ctx)
                order.append("exit a")
                return result

        class B(Policy):
            name, description = "b", "b"

            def around_retrieve(self, ctx, call_next):
                order.append("enter b")
                result = call_next(ctx)
                order.append("exit b")
                return result

        out = PolicySet([A(), B()]).run_retrieve(None, lambda c: order.append("base") or ["x"])

        assert out == ["x"]  # base's return travels back out unchanged
        assert order == ["enter a", "enter b", "base", "exit b", "exit a"]

    def test_empty_set_runs_base_unchanged(self):
        assert PolicySet([]).run_generate(None, lambda c: "RESP") == "RESP"
