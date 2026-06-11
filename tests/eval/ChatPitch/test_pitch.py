"""ChatPitch — EVAL of the generation step (`ChatAdvisor.pitch`) on a real LLM, in isolation.

WHAT IS MEASURED AND WHY
------------------------
pitch() is the GENERATE half of the chat RAG: it receives hits the caller already retrieved,
asks the LLM for structured {intro, recommendations(id+pitch), quick_replies}, validates the
ids against the retrieved set and assembles the customer message — or degrades to a
deterministic fallback when the model fails structured output / no id survives validation.
docs/chat.md records the open finding: in the live smoke, llama3.1-8B produced ZERO valid
recommendations and the fallback fired on every turn. This suite feeds pitch() curated hits
(4-6 realistic Italian games per case) across all 4 strategies × expertise levels and measures
how often the model actually delivers a grounded pitch — plus whether the surviving replies
honor the per-strategy contracts (STRATEGY_K budget, GUIDED's closing question, QUICK_MATCH's
>= 3 concrete proposals, jargon-free language for beginners). No assert: the rates ARE the
deliverable; the conftest aggregates and prints them with a diff vs the previous run.

FALLBACK DETECTION (external, deterministic)
--------------------------------------------
pitch() does not expose a "fallback fired" flag and production code must not be modified, so
we reconstruct the fallback from the inputs and compare. `ChatAdvisor._fallback(hits)` returns
exactly `ChatResponse(message=_plain_pitch(hits[:3]), games=hits[:3], quick_replies=[])`; a
response is classified as fallback iff ALL three fields match that reconstruction: the message
text (built with the same `ChatAdvisor._plain_pitch` helper, so the check tracks production
wording), the ordered ids of the top-3 hits, and empty quick replies.
Limits: a successful LLM reply would be misclassified only if the model returned an empty
intro, empty pitches, no quick replies AND picked exactly the first three hits in retrieval
order — at which point its output is byte-identical to the fallback anyway. There are no
false negatives: the fallback path is fully deterministic.

JARGON CHECK (blunt by design)
------------------------------
`beginner_jargon_free` does a case-insensitive SUBSTRING scan of the reply message against a
small fixed lexicon: "worker placement", "engine building", "deck building", "area control",
"draft". It is intentionally blunt: "draft" also catches "drafting" (still jargon for a
beginner), and a reply that quotes a term while explaining it counts as jargon too. It is a
cheap proxy for "talks like the beginner rules demand", not a fluency judgment.

    docker exec seller-api python -m pytest tests/eval/ChatPitch -q
"""

import json
from pathlib import Path

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.response import ChatResponse
from app.chat.models.strategy import Strategy
from app.chat.routing import STRATEGY_K
from app.models.game_hit import GameHit

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "pitch_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]

# Terms a beginner-facing reply must not contain (see module docstring: blunt substring scan).
_JARGON = ("worker placement", "engine building", "deck building", "area control", "draft")


def _is_fallback(response: ChatResponse, hits: list[GameHit]) -> bool:
    """True iff `response` is byte-identical to `ChatAdvisor._fallback(hits)` (see module
    docstring for why this reconstruction is reliable and where it could misclassify)."""
    return (
        response.message == ChatAdvisor._plain_pitch(hits[:3])
        and response.quick_replies == []
        and [g.id_product for g in response.games] == [h.id_product for h in hits[:3]]
    )


class TestPitch:
    """12 curated cases (4 strategies × beginner/intermediate/advanced), recorded for the
    session report. The per-case booleans feed the conftest aggregation; out-of-scope checks
    are recorded as None so each rate is averaged only over its own cases."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, advisor, pitch_llm, case, record_pitch):
        """Run the production pitch() with the callback-free LLM override and record the
        per-case booleans (no assert: baseline measurement first, thresholds come after
        the numbers are in)."""
        hits = [GameHit(**h) for h in case["hits"]]
        response = advisor.pitch(
            case["message"], hits,
            strategy=case["strategy"], expertise_level=case["expertise_level"],
            history=case["history"], llm=pitch_llm,
        )

        fallback = _is_fallback(response, hits)
        k = STRATEGY_K[Strategy(case["strategy"])]
        lowered = response.message.lower()
        jargon_found = [] if fallback else [t for t in _JARGON if t in lowered]

        record_pitch({
            "case": case["id"],
            "strategy": case["strategy"],
            "expertise_level": case["expertise_level"],
            "n_hits": len(hits),
            "n_games": len(response.games),
            "k": k,
            "fallback": fallback,
            "within_k": None if fallback else len(response.games) <= k,
            "asks_question": (None if fallback or case["strategy"] != "GUIDED"
                              else "?" in response.message),
            "proposes_enough": (None if fallback or case["strategy"] != "QUICK_MATCH"
                                or len(hits) < 3 else len(response.games) >= 3),
            "jargon_free": (None if fallback or case["expertise_level"] != "beginner"
                            else not jargon_found),
            "jargon_found": jargon_found,
            "games": [g.name for g in response.games],
            "quick_replies": response.quick_replies,
            "message": response.message,
            "request": case["message"],
            "hits": [h.name for h in hits],
            "note": case["note"],
        })
