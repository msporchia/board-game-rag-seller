"""ComplexityChoice — "complessità bassa/media/alta" → a complexity range (tested in isolation)."""

import pytest

from app.chat.choices.complexity_choice import ComplexityChoice

_C = ComplexityChoice()


def _parse(text: str):
    match = _C.pattern.search(text)
    return _C.to_filter(match) if match else None


class TestComplexityChoice:
    @pytest.mark.parametrize("word,params", [
        ("bassa", {"max": 2}),
        ("media", {"min": 2, "max": 3}),
        ("alta", {"min": 3}),
    ])
    def test_buckets(self, word, params):
        assert _parse(f"complessità {word}") == ("complexity", params)

    def test_unknown_word_does_not_match(self):
        assert _parse("complessità estrema") is None
