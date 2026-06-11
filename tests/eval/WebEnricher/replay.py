"""WebEnricher record/replay: we freeze the non-deterministic inputs (search + fetch) so the
ONLY variable left is the LLM, and we measure its choices for EACH phase separately.

Why: the real search and pages change over time → a test that calls them live would be unstable
and break on every run. We record ONCE (`recorder.py`) the real response to the query and the
pages; in replay the enricher re-makes its own decisions over those fixed inputs. The 3 phases
are tested separately because each has its own goal (see the 3 `test_*.py`):

  - ranking    = deterministic (whitelist/blocklist/snippet, no LLM)
  - judgment   = the LLM says whether the page is about THE game and whether it's a serious source
  - extraction = the LLM extracts the fact with a quote VERIFIABLE in the text
"""

import json
from pathlib import Path

from app.core.web_search.result import SearchResult
from app.models.game_doc import GameDoc
from tests.eval.WebEnricher.replay_enricher import ReplayWebEnricher
from tests.eval.WebEnricher.replay_search import ReplaySearch

FIXTURES = Path(__file__).parent / "fixtures"


def make_game(fix: dict) -> GameDoc:
    """Rebuilds the fixture's GameDoc with its `missing_info` (triggers the Web)."""
    g = GameDoc.from_dto({"id_product": fix.get("id_product", 0), "name": fix["name"]})
    return g.model_copy(update={"missing_info": list(fix["missing_info"])})


def replay_enricher(fix: dict) -> ReplayWebEnricher:
    return ReplayWebEnricher(fix["pages"], search=ReplaySearch(fix["search_results"]))


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def all_fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("*.json"))


# ---- helpers for the 3 steps ------------------------------------------------

def ranked_results(fix: dict) -> list[SearchResult]:
    """RANKING phase (deterministic): applies `_ranked` to the frozen search_results.
    No network, no LLM — used by the ranking test."""
    enr = replay_enricher(fix)
    raw = [SearchResult(**r) for r in fix["search_results"]]
    return enr._ranked(raw)


def judge_page(enricher: ReplayWebEnricher, fix: dict, url: str) -> dict | None:
    """JUDGMENT phase (LLM): asks the LLM is_this_game/is_serious on the fixture's `url` page.
    Returns the raw dict (`is_this_game`, `is_serious`, `found`) or `None` if parsing fails."""
    text = fix["pages"].get(url, "")
    if not text:
        return None
    return enricher._run_llm(fix["name"], list(fix["missing_info"]), text)


def extract_from_page(enricher: ReplayWebEnricher, fix: dict, url: str) -> dict:
    """EXTRACTION phase (LLM): full extraction+validation pipeline over the page.
    Returns `{info: {"value","quote"}}` with only the stuff whose quote is really in the text
    (anti-hallucination). `{}` if not relevant/not serious/parse failed."""
    text = fix["pages"].get(url, "")
    if not text:
        return {}
    return enricher._judge_extract(fix["name"], list(fix["missing_info"]), text)
