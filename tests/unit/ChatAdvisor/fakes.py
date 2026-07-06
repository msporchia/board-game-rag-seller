"""Fakes for the ChatAdvisor unit — its two collaborators, offline.

The advisor talks to a retriever (`.search → list[GameHit]`) and a structured LLM
(`.invoke → ChatReply`, i.e. intro + per-game {id, pitch} recommendations). We fake both so
the tests are deterministic and assert the advisor's own logic — grounding/validation,
message assembly, fallback, contract shape — not the model.

`FakeStructuredLLM` returns a preset `ChatReply` (the advisor wires `with_structured_output`,
so the real transport hands back a parsed object, not raw text) — or raises, to drive the
fallback path.
"""

from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeRetriever:
    """Returns a preset list of hits; records the queries it received."""

    def __init__(self, hits: list[GameHit]):
        self.hits = hits
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None, exclude_ids=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        hits = [h for h in self.hits if not exclude_ids or h.id_product not in exclude_ids]
        return hits[:k]


class FakeStructuredLLM:
    """`.invoke()` ignores the prompt and returns a preset ChatReply (or raises).

    `pitch` hands a role-split `[SystemMessage, HumanMessage]` list (SEL-122); we record the
    rendered text so the existing "substring in calls[0]" assertions keep reading the model-facing
    content, while the adversarial tests inspect the role split via `advisor._prompt` directly.
    """

    def __init__(self, reply: ChatReply | None = None, raises: bool = False):
        self.reply = reply
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt) -> ChatReply:
        self.calls.append(prompt if isinstance(prompt, str)
                          else "\n".join(m.content for m in prompt))
        if self.raises:
            raise RuntimeError("LLM transport failure")
        return self.reply
