from dataclasses import dataclass


@dataclass
class Row:
    game: str
    metric: str
    baseline: object
    current: object
    verdict: str            # "improved" | "regressed" | "stable" | "new"
    gate: bool

    @property
    def regressed(self) -> bool:
        return self.verdict == "regressed"
