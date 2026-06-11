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
