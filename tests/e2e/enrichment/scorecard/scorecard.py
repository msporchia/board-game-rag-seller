from dataclasses import asdict

from app.rag.retriever import GameRetriever
from tests.e2e.enrichment.run_result import RunResult
from tests.e2e.enrichment.scorecard.metrics import GameMetrics

SCREEN_K = 10        # first screen: top-K out of ~50 games
RANK_DEPTH = 50      # how deep we look for the game when assigning it a rank


def rank(retriever: GameRetriever, query: str, id_product: int, depth: int = RANK_DEPTH) -> int:
    """1-based position of the game in the results; `depth+1` if it doesn't appear."""
    for i, h in enumerate(retriever.search(query, k=depth), 1):
        if h.id_product == id_product:
            return i
    return depth + 1


class Scorecard:
    """A run's per-game metrics, derived from the real retrievers."""

    def __init__(self, screen_k: int, games: dict[str, GameMetrics]):
        self.screen_k = screen_k
        self.games = games

    @classmethod
    def from_result(cls, result: RunResult, screen_k: int = SCREEN_K) -> "Scorecard":
        games: dict[str, GameMetrics] = {}
        for c in result.cases:
            queries = c.must_find_queries
            rf = [rank(result.retriever_full, q, c.id_product) for q in queries]
            rb = [rank(result.retriever_base, q, c.id_product) for q in queries]
            n = len(queries) or 1
            games[c.slug] = GameMetrics(
                web_fired=c.query in result.served_queries,
                n_extractions=len(result.store.get_extractions(c.id_product)),
                embed_len_full=len(result.full_docs[c.id_product].embed_text or ""),
                embed_len_base=len(result.base_embed[c.id_product]),
                avg_rank_full=round(sum(rf) / n, 2),
                avg_rank_base=round(sum(rb) / n, 2),
                queries_in_screen_full=sum(1 for r in rf if r <= screen_k),
                n_queries=len(queries),
                ranks_full=rf,
                ranks_base=rb,
            )
        return cls(screen_k, games)

    def to_dict(self) -> dict:
        return {"screen_k": self.screen_k,
                "games": {slug: asdict(m) for slug, m in self.games.items()}}

    def table(self) -> str:
        lines = [f"SCORECARD (screen_k={self.screen_k})",
                 f"{'game':<20}{'web':<6}{'in_screen':<11}{'avg_full':<10}{'avg_base':<10}{'extr':<6}{'len_f/len_b'}"]
        for slug, m in self.games.items():
            lines.append(
                f"{slug:<20}{str(m.web_fired):<6}{f'{m.queries_in_screen_full}/{m.n_queries}':<11}"
                f"{m.avg_rank_full:<10}{m.avg_rank_base:<10}{m.n_extractions:<6}"
                f"{m.embed_len_full}/{m.embed_len_base}")
        return "\n".join(lines)
