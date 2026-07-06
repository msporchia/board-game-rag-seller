from typing import Literal

from pydantic import BaseModel, Field

from app.chat.models.customer_context import CustomerContext


class ChatRequest(BaseModel):
    # `max_length` is an abuse guard (SEL-122): a customer turn is a sentence or two, not a payload
    # for prompt-stuffing. Bounded here so an oversized body is rejected before it reaches the model.
    message: str = Field(..., max_length=2000, description="the user's free-text turn")
    # Quick-reply clicks. Phase 4 (stateless) appends them to the retrieval query; Phase 5
    # (with `session_id`) parses them into real hybrid-search filters merged into the session.
    choices: list[str] = []
    k: int = Field(5, ge=1, le=20)
    # Present → stateful Phase 5 path (LangGraph with session memory, keyed by this id).
    # Absent → the original stateless Phase 4 behavior, unchanged.
    session_id: str | None = None
    # Per-request engine override (docs/idee.md §Q): None → the CHAT_ENGINE env default.
    # Only meaningful on the stateful path; what makes shadow runs and A/B tests possible
    # without env churn. "agent" = the experimental tool-calling engine (Phase 6).
    engine: Literal["pipeline", "piloted", "agent"] | None = None
    # Optional per-turn policies, activated BY NAME (docs/idee.md §O): the caller sends e.g.
    # ["christmas_sale", "promote_cooperative"] and the PolicySet resolves them to middleware
    # that wraps the turn's stages. Unknown names are ignored (logged), never an error.
    custom_policy: list[str] = []
    # The customer's commerce state, injected per-turn by the shop BFF (Phase 6, docs/chat.md):
    # received/cart/sent product-id sets the seller uses for the enforced-vs-generated split. The
    # seller never learns the customer's identity — only these id_product sets. Absent → no split.
    customer_context: CustomerContext | None = None
