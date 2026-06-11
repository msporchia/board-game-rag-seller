"""SynthEnricher — unit contract (DETERMINISTIC, fake LLM, no Ollama).

PURPOSE
-------
Synth rewrites `enriched.description` by fusing all the material. With a fake model we can't
judge the prose quality (that's the per-step eval's job), but we CAN pin the contract:
  - the model's output becomes `enriched.description`;
  - the hard-truth `original` is never touched;
  - failure/empty output degrades safely (keep the existing description);
  - the safety length cap is enforced;
  - the prompt is actually fed the certain data + the Curator's extractions.

    docker compose exec seller-api python -m pytest tests/unit/SynthEnricher -q
"""

from tests.factories.game import make_game


class TestSynthContract:
    def test_output_becomes_description(self, make_synth):
        """The model's prose replaces `enriched.description`."""
        synth = make_synth(output="Sintesi densa e fattuale del gioco.")
        game = make_game(description="vecchia descrizione di marketing")
        out = synth.enrich(game)
        assert out.enriched.description == "Sintesi densa e fattuale del gioco."

    def test_original_is_untouched(self, make_synth):
        """Hard-truth invariant: `original` never changes."""
        synth = make_synth(output="riscrittura")
        game = make_game(description="originale")
        out = synth.enrich(game)
        assert out.original.description == "originale"

    def test_empty_output_keeps_existing_description(self, make_synth):
        """Empty model output → safe fallback: keep what we had."""
        synth = make_synth(output="   ")
        game = make_game(description="descrizione esistente")
        out = synth.enrich(game)
        assert out.enriched.description == "descrizione esistente"

    def test_no_material_returns_unchanged(self, make_synth):
        """No certain data, no extractions, no description → nothing to synthesize from."""
        synth = make_synth(output="non dovrebbe essere usato")
        game = make_game(name="X", description="")
        out = synth.enrich(game)
        assert out.enriched.description == ""

    def test_length_cap_enforced(self, make_synth):
        """Output longer than max_chars is truncated (on a word boundary)."""
        long_text = "parola " * 500
        synth = make_synth(output=long_text, max_chars=100)
        game = make_game(description="x")
        out = synth.enrich(game)
        assert len(out.enriched.description) <= 100

    def test_prompt_includes_certain_data_and_extractions(self, make_synth):
        """The material handed to the LLM carries the certain data and the Curator's extractions."""
        synth = make_synth(output="ok")
        game = make_game(description="testo", players=[2, 3, 4], duration_min=45)
        game = game.model_copy(update={"extracted": {"ambientazione/tema": "Toscana"}})
        synth.enrich(game)
        prompt = synth._llm.calls[0]
        assert "DATI CERTI" in prompt and "45 minuti" in prompt
        assert "INFO ESTRATTE" in prompt and "Toscana" in prompt
