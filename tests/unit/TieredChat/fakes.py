"""Fakes local to the TieredChat unit: engines honoring the reply contract."""

from app.chat.models.response import ChatResponse


class FakeEngine:
    """Records every reply() call; returns a preset response or raises."""

    def __init__(self, response: ChatResponse | None = None, raises: bool = False):
        self.response = response or ChatResponse(message="fake", games=[], quick_replies=[])
        self.raises = raises
        self.calls: list[dict] = []

    def reply(self, message, choices=None, k=5, session_id="default",
              custom_policy=None, customer_context=None) -> ChatResponse:
        self.calls.append({"message": message, "choices": choices, "k": k,
                           "session_id": session_id, "custom_policy": custom_policy,
                           "customer_context": customer_context})
        if self.raises:
            raise RuntimeError("primary engine down")
        return self.response
