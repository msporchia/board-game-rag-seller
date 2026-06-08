"""PlayersFilter: player counts the game must support.

`players` in the payload is the EXPLODED list (a 2–4 game is stored as [2,3,4]), so a request for
`vals=[3]` matches it via the set intersection — "the game supports more than I asked" is fine by
construction. The dedicated class is where any player-specific sanity/semantics live; for now it
enforces positive integers.
"""

from app.rag.filters.set.set_filter import SetFilter


class PlayersFilter(SetFilter):
    field = "players"

    def validate(self) -> None:
        super().validate()
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in self.vals):
            raise ValueError("PlayersFilter: player counts must be integers >= 1")
        # TODO(evaluate): cap the upper end? A request for >10 players is almost certainly a
        # bad input (typo / the LLM passing a duration into the players slot) rather than a real
        # party game. Not enforced for now — left flagged so it's clear we considered it.
