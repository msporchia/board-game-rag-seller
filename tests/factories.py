"""Shared test helpers: GameDoc factory + fake LLM transport.

No fixtures here (those live in conftest.py): only importable constructors usable from any
test, so `make_game`/`FakeLLM` work both in tests and in fixtures.
"""

from app.models import GameDoc


def make_game(**overrides) -> GameDoc:
    """Test GameDoc with sensible defaults; `overrides` overrides the DTO fields."""
    dto = {"id_product": 1, "name": "Test Game", "description": "Una descrizione di prova."}
    dto.update(overrides)
    return GameDoc.from_dto(dto)


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Fake LLM transport: `.invoke()` ignores the prompt and always returns the same
    `content`. Makes the LLM-step tests DETERMINISTIC without touching Ollama.
    Records the received prompts in `.calls` for optional asserts."""

    def __init__(self, content: str = ""):
        self.content = content
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> _FakeResponse:
        self.calls.append(prompt)
        return _FakeResponse(self.content)
