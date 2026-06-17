"""ChristmasSale — the generation-stage prompt policy (docs/idee.md §O).

Purpose: lock that it contributes its instruction block to the prompt (via `prompt_blocks`) and
otherwise runs the stage unchanged. The base callable stands in for ChatAdvisor.pitch, so the
test asserts the block reached generation without a real advisor/LLM.
"""

from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy_set import PolicySet


class TestChristmasSale:
    def test_appends_a_gift_block_to_the_prompt_blocks(self):
        captured: dict = {}

        def base(ctx):
            captured["blocks"] = list(ctx.prompt_blocks)
            return "RESP"

        ctx = GenerationContext(advisor=None, message="un regalo", hits=[])
        out = PolicySet.from_names(["christmas_sale"]).run_generate(ctx, base)

        assert out == "RESP"
        assert any("saldi di Natale" in block for block in captured["blocks"])

    def test_does_not_add_blocks_when_inactive(self):
        captured: dict = {}

        def base(ctx):
            captured["blocks"] = list(ctx.prompt_blocks)
            return "RESP"

        ctx = GenerationContext(advisor=None, message="un regalo", hits=[])
        PolicySet([]).run_generate(ctx, base)

        assert captured["blocks"] == []
