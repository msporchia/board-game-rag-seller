"""GenerationContext — the live, mutable state of one turn's generation stage.

Policies wrapping `around_generate` read and mutate this freely: append instructions to
`prompt_blocks` (injected into the prompt under a POLICY ATTIVE header), swap `llm`, reshape
`hits`, or rewrite the returned `ChatResponse`. `execute()` is the stage's real work — the
grounded `ChatAdvisor.pitch`, with the accumulated `prompt_blocks` handed in as `extra_blocks`.

`advisor` is typed only for the checker (TYPE_CHECKING) to avoid a runtime import cycle:
advisor.py builds a GenerationContext, so this module must not import advisor at load time.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.chat.models.customer_context import CustomerContext
from app.chat.models.response import ChatResponse
from app.models.game_hit import GameHit

if TYPE_CHECKING:
    from app.chat.advisor import ChatAdvisor


@dataclass
class GenerationContext:
    advisor: "ChatAdvisor"
    message: str
    hits: list[GameHit]
    strategy: str | None = None
    expertise: str | None = None
    history: str | None = None
    llm: object | None = None
    prompt_blocks: list[str] = field(default_factory=list)
    # The customer's commerce state for this turn (Phase 6): pitch applies the enforced-vs-
    # generated split. A policy may read/reshape it before generation, like any other field.
    customer_context: CustomerContext | None = None

    def execute(self) -> ChatResponse:
        """Run the grounded pitch with the policy-accumulated prompt blocks."""
        return self.advisor.pitch(
            self.message, self.hits, strategy=self.strategy,
            expertise_level=self.expertise, history=self.history, llm=self.llm,
            extra_blocks=self.prompt_blocks, customer_context=self.customer_context,
        )
