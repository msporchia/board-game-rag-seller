"""ChristmasSale — a generation-stage policy: bias the pitch toward gift framing.

Wraps `around_generate` to append one instruction block to the prompt; grounding is untouched
(the block can only reshape the prose, not invent games or prices).
"""

from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy import Policy

_GIFT_BLOCK = (
    "Campagna attiva: saldi di Natale. Se ci sono più giochi adatti, rendi la risposta più "
    "orientata al regalo e alla decisione rapida. Non inventare prezzi, sconti o disponibilità: "
    "parla solo di convenienza dell'occasione e di perché il gioco è facile da scegliere/regalare."
)


class ChristmasSale(Policy):
    name = "christmas_sale"
    description = "Bias the pitch toward gift framing and a quick decision (no invented prices)."

    def around_generate(self, ctx: GenerationContext, call_next):
        ctx.prompt_blocks.append(_GIFT_BLOCK)
        return call_next(ctx)
