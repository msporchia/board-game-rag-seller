from dataclasses import dataclass, field


@dataclass
class GameMetrics:
    """A single game's metrics (all serializable)."""

    web_fired: bool
    n_extractions: int
    embed_len_full: int
    embed_len_base: int
    avg_rank_full: float
    avg_rank_base: float
    queries_in_screen_full: int
    n_queries: int
    ranks_full: list[int] = field(default_factory=list)
    ranks_base: list[int] = field(default_factory=list)
