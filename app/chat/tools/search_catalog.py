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
    "Cerca giochi da tavolo nel catalogo del negozio. Passa una `query` descrittiva nel "
    "linguaggio del catalogo (tema, meccaniche, tipo di esperienza, per chi è) e, SOLO se il "
    "cliente li ha dichiarati, i vincoli players / max_minutes / youngest_player_age. "
    "Restituisce i giochi più affini. Chiama questo strumento prima di rispondere: puoi "
    "proporre solo giochi che esso restituisce."
)


class SearchCatalogTool:
    def __init__(self, retriever: GameRetriever | None = None, k: int = 5):
        self.retriever = retriever or GameRetriever()
        self.k = k
        self.calls: list[SearchIntent] = []

    def run(self, query: str = "", players: int | None = None,
            max_minutes: int | None = None, youngest_player_age: int | None = None
            ) -> list[GameHit]:
        """Execute one model-requested search. Reuses SearchIntent's constraint→filter mapping."""
        intent = SearchIntent(query=query, players=players, max_minutes=max_minutes,
                              youngest_player_age=youngest_player_age)
        self.calls.append(intent)
        spec = intent.to_filters_spec()
        filters = SearchFilters.from_dict(spec) if spec else None
        return self.retriever.search(intent.query or query, k=self.k, filters=filters)

    def as_tool(self) -> StructuredTool:
        """The bindable LangChain tool (`llm.bind_tools([tool.as_tool()])`)."""
        return StructuredTool.from_function(
            func=self.run, name="search_catalog", description=_DESCRIPTION,
            args_schema=SearchIntent,
        )
