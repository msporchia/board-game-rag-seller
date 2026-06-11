"""Domain Pydantic schemas — one class per module, import what you need:

- `game_data.GameData`: flat shape of a game (the DTO fields). Used for both `original`
  and `enriched`.
- `game_doc.GameDoc`: working record = original (hard-truth, immutable by convention) +
  enriched (working copy that the pipeline steps fill/transform) + embed_text (text built
  by a compose step). Keeping `original` means we never lose the source and can verify
  the hard-truth.
- `game_hit.GameHit`: a search result (game payload + score).

See docs/pipeline-dati.md.
"""
