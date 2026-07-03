"""AppendSynthEnricher: the APPEND counter-proof of the text-budget experiments (SEL-144).

Measurement variant, NOT production: the synthesis is appended to the full description instead
of replacing it — nothing the source gave us is destroyed, the fused layer is added on top. It
measured best global ordering (err 0.18, ledger row 8 in docs/experiments.md) but was REJECTED
on concept: with append the untrusted source text still reaches the embedder, and the length
normalization (no game advantaged by verbose marketing) is lost. It stays runnable
(`--pipeline synth-append`) so the decision can be re-litigated with numbers at any time.
"""

from app.ingestion.enricher.synth import SynthEnricher
from app.models.game_doc import GameDoc


class AppendSynthEnricher(SynthEnricher):
    def enrich(self, game: GameDoc) -> GameDoc:
        before = (game.enriched.description or "").strip()
        out = super().enrich(game)
        after = (out.enriched.description or "").strip()
        if before and after and after != before:
            return out.with_enriched(description=before + "\n\n" + after)
        return out
