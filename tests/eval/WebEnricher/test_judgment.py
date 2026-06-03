"""WebEnricher — JUDGMENT phase EVAL (requires Ollama).

PURPOSE
-------
Once the sources are chosen, the LLM must judge each page: is it really about the game "X" (not
a homonym, not something else)? Is it a SERIOUS source (review/entry) or a mere product listing?
It's the gate that avoids extracting from wrong or thin pages.

WHAT IT TESTS
-------------
For each fixture × URL with a filled oracle in `expect.judgment[url]`:
- if `is_this_game` is present in the oracle, the LLM must return it identical;
- same for `is_serious`.

PARTIAL assertion: only what the oracle explicitly declares is tested. A page with no keys
(only `note`) is skipped — the oracle being partial is normal, we assert only what we're sure of.

HOW
---
Search+pages input FROZEN by the recorder → the only variable is the model. We call `_run_llm`
(judgment+extraction in a single prompt, see `web.py`) and look ONLY at the judgment fields.

    docker exec seller-api python -m pytest tests/eval/WebEnricher/test_judgment.py -q
"""

import pytest

from tests.eval.WebEnricher.replay import (
    all_fixtures,
    judge_page,
    load_fixture,
    replay_enricher,
)

pytestmark = pytest.mark.llm


def _cases():
    """One case per (fixture, url) with at least one judgment key in the oracle."""
    cases = []
    for path in all_fixtures():
        fix = load_fixture(path)
        for url, exp in (fix.get("expect", {}).get("judgment", {}) or {}).items():
            asserted = {k for k in ("is_this_game", "is_serious") if k in exp}
            if asserted:
                cases.append(pytest.param(path, url, id=f"{path.stem}::{url}"))
    return cases


CASES = _cases()


@pytest.mark.skipif(not CASES, reason="no `expect.judgment` oracle filled in fixtures")
@pytest.mark.parametrize("path,url", CASES)
class TestWebEnricherJudgment:

    def test_judgment_matches_oracle(self, path, url):
        """[fixture::url] is_this_game / is_serious match the oracle (only the declared fields)."""
        fix = load_fixture(path)
        enr = replay_enricher(fix)
        data = judge_page(enr, fix, url)
        assert data is not None, f"[{fix['name']}::{url}] the LLM did not return valid JSON"

        exp = fix["expect"]["judgment"][url]
        errors = []
        for key in ("is_this_game", "is_serious"):
            if key in exp and bool(data.get(key)) != bool(exp[key]):
                errors.append(f"{key}: expected={exp[key]} now={data.get(key)}")
        assert not errors, (
            f"[{fix['name']}::{url}] {' | '.join(errors)}\nORACLE NOTE: {exp.get('note', '-')}"
        )
