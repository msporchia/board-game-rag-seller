"""Shared test helpers, one per module: `game.make_game` (GameDoc factory), `llm.FakeLLM`
(fake LLM transport), `embeddings.FakeEmbeddings` (deterministic offline embeddings).

No fixtures here (those live in conftest.py): only importable constructors usable from any
test, so they work both in tests and in fixtures.
"""
