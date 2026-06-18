"""SearchCatalogTool — the catalog search exposed as an LLM-callable tool (docs/idee.md §Q).

The groundwork for the agentic engine: the strong model decides WHEN and WITH WHAT WORDS to
search; this tool is the boundary where its decision becomes a real hybrid-search call. It wraps
the same GameRetriever + SearchFilters as every other engine, reusing `SearchIntent` as the
argument schema (query + the declared constraints) and its `to_filters_spec` mapping — so the
"model proposes, code disposes" split (clicks/constraints → filters) is identical to the piloted
engine. `k` is engine-controlled, NOT a model argument: the model chooses what to look for, the
code chooses how many rows return.

`calls` records every search the model asked for (the union feeds grounding; useful for eval).
"""

from langchain_core.tools import StructuredTool

from app.chat.models.intent import SearchIntent
from app.models.game_hit import GameHit
from app.rag.filters.search_filters import SearchFilters
from app.rag.retriever import GameRetriever

_DESCRIPTION = (
    "Cerca giochi da tavolo nel catalogo del negozio. La `query` descrive il gioco SOLO per "
    "tema, meccaniche, tipo di esperienza, per chi è (linguaggio del catalogo). I vincoli "
    "numerici (players / max_minutes / youngest_player_age) vanno negli appositi campi interi, "
    "NON nella query: la ricerca semantica non li recepisce, li applica un filtro esatto. "
    "Restituisce i giochi più affini. Chiama questo strumento prima di rispondere: puoi "
    "proporre solo giochi che esso restituisce."
)


class SearchCatalogTool:
    def __init__(self, retriever: GameRetriever | None = None, k: int = 5):
        self.retriever = retriever or GameRetriever()
        self.k = k
        self.calls: list[SearchIntent] = []

    def run(self, query: str = "", players=None, max_minutes=None,
            youngest_player_age=None) -> list[GameHit]:
        """Execute one model-requested search. Reuses SearchIntent's constraint→filter mapping.

        Robust to the model's imperfect tool args (the model proposes, the code disposes): a
        constraint that won't coerce to an int — e.g. qwen2.5 sometimes emits `{"max": 180}`
        instead of `180` — is dropped rather than crashing the turn (`_as_int`).
        """
        intent = SearchIntent(
            query=query if isinstance(query, str) else (str(query) if query else ""),
            players=self._as_int(players), max_minutes=self._as_int(max_minutes),
            youngest_player_age=self._as_int(youngest_player_age))
        self.calls.append(intent)
        spec = intent.to_filters_spec()
        filters = SearchFilters.from_dict(spec) if spec else None
        return self.retriever.search(intent.query, k=self.k, filters=filters)

    @staticmethod
    def _as_int(value) -> int | None:
        """Coerce a model-supplied constraint to int, or None. Unwraps a dict like {"max": 180}
        (a single scalar value) — the model occasionally nests the number it meant to pass."""
        if isinstance(value, dict):
            value = next((v for v in value.values() if not isinstance(v, (dict, list))), None)
        try:
            return int(value) if value is not None and not isinstance(value, bool) else None
        except (TypeError, ValueError):
            return None

    def as_tool(self) -> StructuredTool:
        """The bindable LangChain tool (`llm.bind_tools([tool.as_tool()])`)."""
        return StructuredTool.from_function(
            func=self.run, name="search_catalog", description=_DESCRIPTION,
            args_schema=SearchIntent,
        )
