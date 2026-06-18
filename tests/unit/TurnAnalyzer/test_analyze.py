"""TurnAnalyzer — the "read the customer" step extracted from ChatGraph.

Purpose: lock the component's own logic with the LLM faked — the prompt carries the conversation,
a successful call returns the model's TurnAnalysis, and a failed call returns the fallback (the
previous analysis) so a transient analyzer failure never kills the turn.
"""

from app.chat.analyzer import TurnAnalyzer
from app.chat.models.analysis import TurnAnalysis

_FALLBACK = TurnAnalysis(enthusiasm="medium", decisiveness="undecided",
                         expertise_level="beginner", reply_style="short")


class _FakeLLM:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str):
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("analyze down")
        return self.result


class TestTurnAnalyzer:
    def test_prompt_carries_conversation_and_message(self):
        prompt = TurnAnalyzer.prompt(["utente: ciao"], "un cooperativo")
        assert "utente: ciao" in prompt and "un cooperativo" in prompt
        assert "CONVERSAZIONE FINORA" in prompt

    def test_empty_history_marks_the_start(self):
        assert "(inizio conversazione)" in TurnAnalyzer.prompt([], "ciao")

    def test_returns_the_models_analysis(self):
        result = TurnAnalysis(enthusiasm="high", decisiveness="decided",
                              expertise_level="advanced", reply_style="long")
        analyzer = TurnAnalyzer(llm=_FakeLLM(result=result))

        assert analyzer.analyze(["h"], "m", _FALLBACK) is result

    def test_failure_returns_the_fallback(self):
        analyzer = TurnAnalyzer(llm=_FakeLLM(raises=True))

        assert analyzer.analyze(["h"], "m", _FALLBACK) is _FALLBACK
