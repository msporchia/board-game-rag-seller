"""Quick-reply clicks → SearchFilters fragments ("a click becomes a new filter").

Phase 4 folded `choices` into the retrieval query string; Phase 5 parses them into real
structured constraints. The parsing is DETERMINISTIC (regex, no LLM) because we control both
ends: the pitch prompt instructs the model to emit quick replies in these exact machine-parseable
shapes, so the parser only has to recognize what we ourselves generate:

    "per 2 giocatori"     → players    {"vals": [2]}
    "max 60 minuti"       → duration   {"max": 60}
    "dai 8 anni"          → age        {"max": 8}     (age_min <= 8 → suitable for an 8-year-old)
    "senza espansioni"    → expansions {"val": False}
    "complessità bassa"   → complexity {"max": 2}     (media → 2..3, alta → >= 3, BGG 1..5)

Anything that doesn't match (free-form refinements like "Sorprendimi") is returned as a leftover
and folded into the retrieval query, exactly like Phase 4 — a graceful degradation, never a drop.
"""

import re

# (pattern, spec-builder) pairs; first match wins. Specs are `SearchFilters.from_dict` fragments.
_RULES: list[tuple[re.Pattern, callable]] = [
    (re.compile(r"\bper\s+(\d+)\s+giocator\w*", re.IGNORECASE),
     lambda m: ("players", {"vals": [int(m.group(1))]}) if int(m.group(1)) >= 1 else None),
    (re.compile(r"\bmax\s+(\d+)\s+min\w*", re.IGNORECASE),
     lambda m: ("duration", {"max": int(m.group(1))}) if int(m.group(1)) > 0 else None),
    (re.compile(r"\bda[i]?\s+(\d+)\s+anni\b", re.IGNORECASE),
     lambda m: ("age", {"max": int(m.group(1))}) if int(m.group(1)) > 0 else None),
    (re.compile(r"\bsenza\s+espansioni\b", re.IGNORECASE),
     lambda m: ("expansions", {"val": False})),
    (re.compile(r"\bcomplessit\w*\s+(bassa|media|alta)\b", re.IGNORECASE),
     lambda m: ("complexity", {"bassa": {"max": 2}, "media": {"min": 2, "max": 3},
                               "alta": {"min": 3}}[m.group(1).lower()])),
]


def parse_choices(choices: list[str] | None) -> tuple[dict, list[str]]:
    """Split clicks into (filters_spec fragment, unparsed leftovers).

    The fragment is keyed per filter name, so merging it into the session's accumulated spec
    means "the latest click on a dimension wins" (clicking "per 4 giocatori" after
    "per 2 giocatori" replaces the player constraint, it does not pile up).
    """
    spec: dict = {}
    leftovers: list[str] = []
    for choice in choices or []:
        parsed = _parse_one(choice)
        if parsed:
            name, params = parsed
            spec[name] = params
        else:
            leftovers.append(choice)
    return spec, leftovers


def _parse_one(choice: str) -> tuple[str, dict] | None:
    for pattern, build in _RULES:
        m = pattern.search(choice)
        if m:
            result = build(m)
            if result:  # builder may reject nonsense values (e.g. "per 0 giocatori")
                return result
    return None
