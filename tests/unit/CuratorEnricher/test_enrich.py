"""CuratorEnricher — how `enrich()` applies the canonical output of `assess()` to the GameDoc.

PURPOSE: pin down the application contract, independent of the prompt: the Curator derives
`{estratti, presenti, mancanti}` (stable API) → `enrich()` writes them onto the GameDoc.

WHAT IT TESTS
- `original` (hard-truth) never touched.
- `enriched.description` is NOT touched (the synthesis is in `SynthEnricher`).
- `missing_info` reflects the `mancanti` (input for the WebEnricher).
- `extracted` receives the validated extractions, **merged** with any previous ones
  (new same-name keys overwrite).
- The mechanics from `estratti` go into `tags` ONLY if empty (CERTAIN DATA wins).
- LLM-fail on all batches → sane behavior: nothing in estratti, the asked labels in mancanti
  (feeds the Web fallback), structurally-present ones stay in presenti.

HOW: fake LLM via `make_curator(payload)` + `per_label(...)`. For the tests where verbatim
validation matters, we build a `make_game(description=...)` consistent with the fake payload's
quote.
"""

from tests.factories.game import make_game


class TestCuratorEnrich:
    def test_original_never_touched(self, make_curator, per_label):
        """The hard-truth stays intact."""
        g = make_game(description="ORIG marketing lungo", tags=["X"], duration_min=60)
        out = make_curator(per_label()).enrich(g)
        assert out.original.description == "ORIG marketing lungo"
        assert out.original.tags == ["X"]

    def test_description_is_not_touched(self, make_curator, per_label):
        """The Curator no longer synthesizes the description: that's the SynthEnricher's job."""
        out = make_curator(per_label()).enrich(make_game(description="descrizione lunga"))
        assert out.enriched.description == "descrizione lunga"

    def test_missing_info_includes_only_labels_asked_to_llm(self, make_curator, per_label):
        """`missing_info` contains ONLY the labels asked to the LLM and not confirmed.
        The structured ones ALREADY in the certain data don't end up there (we apply them)."""
        g = make_game(tags=["Coop"], duration_min=60, complexity="Medio", players=[2, 3])
        # all the structured ones are in the certain data → the LLM gets only the 3 descriptive
        # with per_label() default → all NESSUNO → all 3 in mancanti
        out = make_curator(per_label()).enrich(g)
        assert set(out.missing_info) == {"ambientazione/tema", "genere", "a chi è adatto"}

    def test_extracted_saved_on_gamedoc_with_valid_quote(self, make_curator, per_label):
        """Validated extractions (quote verbatim in the desc) end up in `game.extracted`."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "fantasy medievale",
                                    "valore_normalizzato": "fantasy"},
        })
        g = make_game(description="Avventura fantasy medievale tra cavalieri.")
        out = make_curator(payload).enrich(g)
        assert out.extracted == {"ambientazione/tema": "fantasy"}

    def test_extracted_merges_with_previous(self, make_curator, per_label):
        """Pre-existing extractions in `game.extracted` are PRESERVED; new same-name ones
        overwrite."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "fantasy", "valore_normalizzato": "fantasy"},
        })
        g = make_game(description="fantasy").model_copy(update={
            "extracted": {"vecchio": "ok", "ambientazione/tema": "vecchio-tema"},
        })
        out = make_curator(payload).enrich(g)
        assert out.extracted == {"vecchio": "ok", "ambientazione/tema": "fantasy"}

    def test_present_tags_not_overwritten(self, make_curator, per_label):
        """CERTAIN DATA wins: present tags not overwritten by the deduced ones.
        When tags is non-empty, the Curator doesn't even ask the LLM for 'meccaniche principali'
        (it's in `structurally_present`)."""
        out = make_curator(per_label()).enrich(make_game(description="cooperativo",
                                                          tags=["Originali"]))
        assert out.enriched.tags == ["Originali"]

    def test_tags_filled_from_estratti_meccaniche_when_empty(self, make_curator, per_label):
        """Empty tags → the extracted mechanics are used (split on comma)."""
        payload = per_label(**{
            "meccaniche principali": {"citazione": "cooperativo, lancio di dadi",
                                       "valore_normalizzato": "Cooperativo, Lancio di dadi"},
        })
        g = make_game(description="cooperativo, lancio di dadi", tags=[])
        out = make_curator(payload).enrich(g)
        assert out.enriched.tags == ["Cooperativo", "Lancio di dadi"]

    def test_other_estratti_dont_overwrite_struct_fields(self, make_curator, per_label):
        """Extracted strings (duration/players/complexity) stay in `extracted` but do NOT
        populate `duration_min`/`players`/`complexity` without a dedicated parser."""
        payload = per_label(**{
            "durata":           {"citazione": "circa 90 minuti", "valore_normalizzato": "90 minuti"},
            "numero giocatori": {"citazione": "da 1 a 4",          "valore_normalizzato": "1-4"},
            "complessità":      {"citazione": "media",             "valore_normalizzato": "media"},
        })
        g = make_game(description="circa 90 minuti, da 1 a 4 giocatori, complessità media",
                      duration_min=None, players=[], complexity=None, tags=["X"])
        out = make_curator(payload).enrich(g)
        assert out.enriched.duration_min is None
        assert out.enriched.players == []
        assert out.enriched.complexity is None
        assert out.extracted == {"durata": "90 minuti", "numero giocatori": "1-4",
                                  "complessità": "media"}

    def test_llm_parse_error_yields_safe_state(self, make_curator):
        """LLM/parse fails on ALL batches → no estratti, the asked labels go into
        `missing_info` (feeds the WebEnricher), structurally-present ones stay in presenti."""
        g = make_game(description="orig", tags=["X"], duration_min=60,
                      complexity="Medio", players=[2, 3])
        out = make_curator("non-json {").enrich(g)
        assert out.extracted == {}
        # structure: no structured one is missing → only the 3 descriptive ones are "needed"
        assert set(out.missing_info) == {"ambientazione/tema", "genere", "a chi è adatto"}
        # original intact, enriched does not degrade
        assert out.original.description == "orig"
        assert out.enriched.tags == ["X"]
