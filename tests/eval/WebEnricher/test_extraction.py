"""WebEnricher — EXTRACTION phase EVAL (requires Ollama).

PURPOSE
-------
On the pages judged good (relevant+serious), the LLM must extract the requested fact with a
VERBATIM QUOTE in the text (anti-hallucination). The value may vary in the details (e.g.
'Toscana' vs 'Tuscany') so the oracle asserts only the "gist" via substring: the fact must be
there, the quote must be real.

WHAT IT TESTS
-------------
For each fixture × URL × info declared in `expect.extraction[url][info]`:
- the info is present in the output of `_judge_extract` (passes the relevance/seriousness/quote
  filter);
- if `value_contains` is given, the substring is present in the `value` (case-insensitive);
- if `quote_in_text: true`, the returned `quote` is really in the page text (redundant with the
  internal filter, but explicit as an assert: it would reveal accidental removals of the check).

PARTIAL assertion: only what the oracle explicitly declares is tested.

HOW
---
Search+pages input FROZEN; the ONLY variable = LLM. Full `_judge_extract` pipeline (judgment +
extraction + quote validation) over the page text.

    docker exec seller-api python -m pytest tests/eval/WebEnricher/test_extraction.py -q
"""

import pytest

from tests.eval.WebEnricher.replay import (
    all_fixtures,
    extract_from_page,
    load_fixture,
    replay_enricher,
)

pytestmark = pytest.mark.llm


def _normalize(s: str) -> str:
    return " ".join(s.lower().split())


def _cases():
    """One case per (fixture, url, info) with at least one assert key in the oracle."""
    cases = []
    for path in all_fixtures():
        fix = load_fixture(path)
        per_url = fix.get("expect", {}).get("extraction", {}) or {}
        for url, infos in per_url.items():
            for info, exp in infos.items():
                if info == "note" or not isinstance(exp, dict):
                    continue
                asserted = {k for k in ("value_contains", "quote_in_text") if k in exp}
                if asserted:
                    cases.append(pytest.param(path, url, info, id=f"{path.stem}::{url}::{info}"))
    return cases


CASES = _cases()


@pytest.mark.skipif(not CASES, reason="no `expect.extraction` oracle filled in fixtures")
@pytest.mark.parametrize("path,url,info", CASES)
class TestWebEnricherExtraction:

    def test_extraction_matches_oracle(self, path, url, info):
        """[fixture::url::info] the fact is extracted, substring in the value, quote in the text."""
        fix = load_fixture(path)
        enr = replay_enricher(fix)
        found = extract_from_page(enr, fix, url)

        exp = fix["expect"]["extraction"][url][info]
        note = exp.get("note", "-")

        assert info in found, (
            f"[{fix['name']}::{url}] info '{info}' expected but not extracted. "
            f"Extracted: {sorted(found)}\nNOTE: {note}"
        )
        payload = found[info]
        value, quote = payload.get("value", ""), payload.get("quote", "")

        if "value_contains" in exp:
            needle = exp["value_contains"]
            assert needle.lower() in value.lower(), (
                f"[{fix['name']}::{url}::{info}] value='{value}' does not contain '{needle}'\nNOTE: {note}"
            )
        if exp.get("quote_in_text"):
            text = fix["pages"].get(url, "")
            assert _normalize(quote) in _normalize(text), (
                f"[{fix['name']}::{url}::{info}] quote='{quote}' is not verbatim in the text\nNOTE: {note}"
            )
