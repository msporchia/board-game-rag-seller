"""CustomerContext — the customer's commerce state, injected per-turn by the shop BFF (Phase 6).

The seller stays ignorant of customer *identity*: it never receives a customer id, only sets of
`id_product` the BFF derives server-side from the customer's orders and cart. Those ids are the
same ints `GameHit.id_product` carries, so they line up with retrieved hits with no mapping.

The point of the feature is the *enforced-vs-generated split* — the same "the model proposes, the
code disposes" discipline the rest of the chat already runs on (docs/chat.md):

- **received** — games the customer already owns/bought. Excluded **deterministically at
  RETRIEVAL** (`received_products` → `RetrievalContext.exclude_ids` → Qdrant `must_not`), so an
  owned game never even enters the candidate set the model sees. This is the *enforced* half —
  code, not a prompt; the model never gets the chance to re-pitch a game the customer already has.
- **cart** — games already in the cart. NOT excluded: framed in the prompt as "already chosen",
  so the model treats them as in-progress instead of pitching them as a fresh idea.
- **sent** — games on the way (e.g. a gift already shipped). Framed like the cart: "on the way",
  not a new idea. Cart/sent are the *generated* half — a soft instruction the model phrases.

Why received is hard and cart/sent are soft: owning a game is a fact (re-pitching it is just
wrong), while "it's in your cart" is conversational nuance the model is free to weave in.
"""

from pydantic import BaseModel

from app.models.game_hit import GameHit


class CustomerContext(BaseModel):
    received_products: list[int] = []  # already owned/bought → excluded deterministically
    sent_products: list[int] = []      # on the way (gift shipped) → framed, not excluded
    cart_products: list[int] = []      # already in the cart → framed as chosen, not re-pitched

    def is_empty(self) -> bool:
        return not (self.received_products or self.sent_products or self.cart_products)

    def framing_block(self, hits: list[GameHit]) -> str | None:
        """Generated-side framing for cart/sent games that are on the table this turn.

        Only games that actually survived into `hits` are named — there is no point telling the
        model about a cart game it isn't being shown. Returns None when nothing applies (no block
        is injected). The hard rule (received exclusion) is enforced separately, in code.
        """
        names = {h.id_product: h.name for h in hits}
        in_cart = [names[i] for i in self.cart_products if i in names]
        on_way = [names[i] for i in self.sent_products if i in names]
        lines: list[str] = []
        if in_cart:
            lines.append(
                f"Il cliente ha GIÀ nel carrello: {', '.join(in_cart)}. Non riproporli come "
                "nuova idea — semmai trattali come una scelta che ha già fatto."
            )
        if on_way:
            lines.append(
                f"Il cliente ha già in arrivo (regalo spedito): {', '.join(on_way)}. Non "
                "riproporli come nuova idea."
            )
        return "\n".join(lines) or None
