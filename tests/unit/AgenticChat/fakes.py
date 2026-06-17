"""Fakes local to the AgenticChat unit — a tool-calling LLM plus the advisor's collaborators.

`FakeToolCallingLLM` is the agent's brain: `bind_tools` records the tools and returns self, and
`invoke` replays a scripted queue of AIMessages (tool-call rounds, then a final no-tool-call
message that ends the loop). The retriever and pitch model are the usual ChatAdvisor fakes, so
the test asserts the LOOP — tool calls → union of hits → grounded pitch — not the models.
"""

from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeToolCallingLLM:
    def __init__(self, scripted: list):
        self.scripted = list(scripted)
        self.bound_tools = None
        self.invocations: list = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.invocations.append(messages)
        return self.scripted.pop(0) if len(self.scripted) > 1 else self.scripted[0]


class FakeBatchRetriever:
    """Returns scripted result lists in order (one per search call); records (query, k, filters)."""

    def __init__(self, results: list[list[GameHit]]):
        self.results = list(results)
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        batch = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        return batch[:k]


class FakePitchLLM:
    """`.invoke()` returns a preset ChatReply; records the prompts it saw."""

    def __init__(self, reply: ChatReply):
        self.reply = reply
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> ChatReply:
        self.calls.append(prompt)
        return self.reply
