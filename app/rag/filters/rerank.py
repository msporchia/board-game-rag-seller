"""Soft-mode re-ranking: boost the games that satisfy the soft constraints, without excluding."""

from typing import Callable

# Multiplicative boost applied per satisfied soft constraint when re-ranking (strict=False).
SOFT_BOOST = 0.1


def rerank_soft(results: list[tuple], predicates: list[Callable[[dict], bool]]) -> list[tuple]:
    """Stable re-rank of [(Document, score), ...]: each satisfied soft predicate multiplies the
    score by (1 + SOFT_BOOST). Non-matching points (incl. those missing the field) keep their
    score — soft never penalizes, only promotes. Ties preserve the original (semantic) order."""
    if not predicates:
        return results

    def adjusted(item):
        doc, score = item
        payload = doc.metadata or {}
        matched = sum(1 for pred in predicates if pred(payload))
        return score * (1 + SOFT_BOOST) ** matched

    return sorted(results, key=adjusted, reverse=True)
