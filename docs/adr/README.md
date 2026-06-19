# Architecture Decision Records

Short records of the **non-obvious** decisions in this repo — the ones that had a defensible
alternative we rejected. Each ADR names that alternative and the trade-off it cost us; a decision
with no real alternative (FastAPI, Docker Compose) is not recorded here, on purpose.

These are written **post-hoc**: they reconstruct decisions already made and visible in the code,
not a plan written ahead of it. The point is to make the reasoning legible — to show *why* a
fork was taken, not just *that* it was.

| # | Decision | The fork |
|---|----------|----------|
| [0001](0001-enrich-embed-text-over-stronger-embedder.md) | Enrich the text we embed, instead of reaching for a stronger embedder | input vs. model |
| [0002](0002-grounding-enforced-in-code.md) | Enforce anti-hallucination in code; assemble the reply in code | trust the prompt vs. trust the code |
| [0003](0003-interchangeable-chat-engines.md) | Ship several interchangeable chat engines on one bench | pick one engine vs. measure the curve |
| [0004](0004-rank-not-score.md) | Measure retrieval by ranking, never by an absolute score | calibrated threshold vs. relative order |
