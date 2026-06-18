"""Fakes local to the PilotedChat unit — the engine's four collaborators, offline.

The piloted loop talks to two structured LLM steps (intent, retry), one retriever and one
pitch model; we fake all four so the tests assert the LOOP's own logic — intent-as-query,
the explicit zero-result retry, the search budget, the informed no-match — not the models.

`FakeSearchRetriever` takes a QUEUE of result lists (one per search call, the last one
repeating), so a test can script "first search empty, second search finds" — the shape the
retry loop exists for.
"""

from app.chat.models.intent import SearchIntent
from app.chat.models.reply import ChatReply
from app.chat.models.retry import RetryDecision
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeSearchRetriever:
    """Returns the scripted result lists in order (cut to k); records (query, k, filters)."""

    def __init__(self, results: list[list[GameHit]]):
        self.results = list(results)
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None, exclude_ids=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        batch = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        batch = [h for h in batch if not exclude_ids or h.id_product not in exclude_ids]
        return batch[:k]


class FakeIntentLLM:
    """`.invoke()` returns the scripted SearchIntent queue, repeating the last entry."""

    def __init__(self, intents: list[SearchIntent] | None = None, raises: bool = False):
        self.intents = list(intents or [])
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> SearchIntent:
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("intent transport failure")
        if not self.intents:
            return SearchIntent(query="query riformulata dal modello")
        return self.intents.pop(0) if len(self.intents) > 1 else self.intents[0]


class FakeRetryLLM:
    """`.invoke()` returns the scripted RetryDecision queue, repeating the last entry."""

    def __init__(self, decisions: list[RetryDecision] | None = None, raises: bool = False):
        self.decisions = list(decisions or [])
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> RetryDecision:
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("retry transport failure")
        if not self.decisions:
            return RetryDecision(no_match=True)
        return self.decisions.pop(0) if len(self.decisions) > 1 else self.decisions[0]


class FakePitchLLM:
    """`.invoke()` returns a preset ChatReply; records prompts."""

    def __init__(self, reply: ChatReply):
        self.reply = reply
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> ChatReply:
        self.calls.append(prompt)
        return self.reply
