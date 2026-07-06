"""Fakes for the ChatGraph unit — the graph's four collaborators, offline.

The graph talks to three LLM-shaped collaborators (the analyzer, the default pitch model, the
strong escalation model) and one retriever; we fake all four so the tests assert the GRAPH's own
logic — routing, clicks→filters, memory, tiering — not the models.

`FakeAnalyzeLLM` takes a QUEUE of TurnAnalysis: one entry per turn, the last one repeating —
so a test can script how the "user" comes across turn by turn.
"""

from app.chat.models.analysis import TurnAnalysis
from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeRetriever:
    """Returns a preset list of hits (cut to k); records (query, k, filters) per call."""

    def __init__(self, hits: list[GameHit]):
        self.hits = hits
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None, exclude_ids=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        hits = [h for h in self.hits if not exclude_ids or h.id_product not in exclude_ids]
        return hits[:k]


class FakeAnalyzeLLM:
    """`.invoke()` returns the scripted TurnAnalysis queue, repeating the last entry."""

    def __init__(self, analyses: list[TurnAnalysis] | None = None, raises: bool = False):
        self.analyses = list(analyses or [])
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> TurnAnalysis:
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("analyzer transport failure")
        if not self.analyses:
            return TurnAnalysis()
        return self.analyses.pop(0) if len(self.analyses) > 1 else self.analyses[0]


class FakeGenLLM:
    """`.invoke()` returns a preset ChatReply; records the rendered prompt text (to assert WHICH
    model ran and which blocks reached it).

    `ChatAdvisor.pitch` hands a role-split `[SystemMessage, HumanMessage]` list (SEL-122); we join
    the contents so the "substring in calls[0]" assertions keep reading the model-facing text.
    """

    def __init__(self, reply: ChatReply):
        self.reply = reply
        self.calls: list[str] = []

    def invoke(self, prompt) -> ChatReply:
        self.calls.append(prompt if isinstance(prompt, str)
                          else "\n".join(m.content for m in prompt))
        return self.reply
