"""GameRetriever ranking — the actual order vs an ORDERED oracle, on production-shaped data.

WHAT IS UNDER EVAL
------------------
`GameRetriever.search` is the step that puts games on the table: the chat's retrieve node
delegates to it after assembling the query. ChatRetrieve already measures the conversational
assembly with a single-target recall@k; this suite isolates the RANKING itself — one realistic
single-shot query per case, full ranking requested, scored against an oracle that states not
just WHICH games should come back but in WHAT ORDER.

WHY AN ORDERED ORACLE
---------------------
Top-k membership is blind to order: a customer shown B,A,C,D got an almost perfect answer,
one shown D,?,?,? got a wrong one, yet plain recall@4 scores the first 4/4 and the second 1/4
without saying how wrong the rest was. NDCG over the oracle window (see `report.RankingReport`)
weighs the deviation by how far it strays — adjacent swaps are nearly free, the expected games
drifting out of the visible window collapses the score.

The corpus is the FROZEN post-pipeline fixture (`games_enriched.json`): the eval must rank the
text the retriever sees in production, not the raw marketing it will never search over. There
is no correctness assert: the first runs establish the baseline; the conftest aggregates mean
NDCG and displacement at session end.

    docker compose exec seller-api python -m pytest tests/eval/GameRetriever -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "ranking_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestRanking:
    """Oracle-ranked realistic queries: the deviation from the expected order is the score."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, retriever, corpus, case, record_ranking):
        """Request the FULL ranking so every oracle game has a rank, then record it."""
        hits = retriever.search(case["query"], k=len(corpus))
        rank_of = {hit.id_product: i + 1 for i, hit in enumerate(hits)}
        name_of = {hit.id_product: hit.name for hit in hits}

        window = len(case["oracle"])
        record_ranking({
            "case": case["id"],
            "query": case["query"],
            "note": case["note"],
            "oracle": [{
                "id": gid,
                "name": name_of.get(gid),
                "expected_pos": pos,
                # unranked only if the id is not in the corpus — surface it as last+1
                "rank": rank_of.get(gid, len(corpus) + 1),
            } for pos, gid in enumerate(case["oracle"], start=1)],
            # what the customer would actually see: the oracle-sized window plus the two
            # ranks below it — the intruders that beat the oracle are the anomaly signal
            "window": [{"id": h.id_product, "name": h.name} for h in hits[:window + 2]],
        })
