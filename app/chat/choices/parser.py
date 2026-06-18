"""ClickParser — quick-reply clicks → SearchFilters fragment + leftovers ("a click becomes a filter").

Phase 4 folded `choices` into the retrieval query string; Phase 5 parses them into real structured
constraints. The parser asks each registered `Choice` (first match wins; patterns don't overlap, so
order is not load-bearing) to recognize the click and produce its filter fragment. Anything no
choice recognizes — free-form refinements like "Sorprendimi" — is returned as a leftover and folded
into the retrieval query, a graceful degradation, never a drop.

    "per 2 giocatori"     → players    {"vals": [2]}
    "max 60 minuti"       → duration   {"max": 60}
    "dai 8 anni"          → age        {"max": 8}
    "senza espansioni"    → expansions {"val": False}
    "complessità bassa"   → complexity {"max": 2}
"""

from app.chat.choices.age_choice import AgeChoice
from app.chat.choices.choice import Choice
from app.chat.choices.complexity_choice import ComplexityChoice
from app.chat.choices.duration_choice import DurationChoice
from app.chat.choices.expansions_choice import ExpansionsChoice
from app.chat.choices.players_choice import PlayersChoice

# The recognized choice types. One instance per type (stateless), tried in order.
REGISTRY: list[Choice] = [
    PlayersChoice(), DurationChoice(), AgeChoice(), ExpansionsChoice(), ComplexityChoice(),
]


class ClickParser:
    """Parses quick-reply clicks into a filter spec. Injectable choice set for tests."""

    def __init__(self, choices: list[Choice] | None = None):
        self.choices = choices if choices is not None else REGISTRY

    def parse(self, clicks: list[str] | None) -> tuple[dict, list[str]]:
        """Split clicks into (filters_spec fragment, unparsed leftovers).

        The fragment is keyed per filter name, so merging it into the session's accumulated spec
        means "the latest click on a dimension wins" (clicking "per 4 giocatori" after "per 2
        giocatori" replaces the player constraint, it does not pile up).
        """
        spec: dict = {}
        leftovers: list[str] = []
        for click in clicks or []:
            fragment = self._parse_one(click)
            if fragment:
                name, params = fragment
                spec[name] = params
            else:
                leftovers.append(click)
        return spec, leftovers

    def _parse_one(self, click: str) -> tuple[str, dict] | None:
        for choice in self.choices:
            match = choice.pattern.search(click)
            if match:
                fragment = choice.to_filter(match)
                if fragment:  # a choice may reject a nonsense value (e.g. "per 0 giocatori")
                    return fragment
        return None
