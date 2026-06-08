"""Single CLI for the enrichment e2e (no more scattered scripts).

    # record/refresh the frozen scraping (network + containers, once)
    docker exec seller-api python -m tests.e2e.enrichment record --ids 160,22,21

    # run the real ingest, print the scorecard and the baseline diff (gate via exit code)
    docker exec seller-api python -m tests.e2e.enrichment run

    # same, but REWRITE the baseline (after an intended improvement → then commit it)
    docker exec seller-api python -m tests.e2e.enrichment run --update-baseline

The `run` subcommand is also what the regression test exercises from pytest; here it is for
eyeballing the numbers and for regenerating the baseline.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from tests.e2e.enrichment.harness import EnrichmentHarness
from tests.e2e.enrichment.recorder import DEFAULT_IDS, Recorder
from tests.e2e.enrichment.scorecard import Baseline, Scorecard


def _cmd_record(args) -> int:
    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    Recorder().record(ids)
    return 0


def _cmd_run(args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "e2e.db")
        result = EnrichmentHarness(db, "e2e_run_full", "e2e_run_base").run()
        try:
            scorecard = Scorecard.from_result(result)
            print("\n" + scorecard.table() + "\n")

            if args.update_baseline:
                Baseline.write(scorecard)
                print(f"baseline updated -> {Baseline.load().path}")
                return 0

            baseline = Baseline.load()
            if baseline is None:
                print("no baseline: run `run --update-baseline` to create it.")
                return 0

            comparison = baseline.compare(scorecard)
            print(comparison.table() + "\n")
            if comparison.has_gating_regression:
                print("REGRESSION beyond tolerance vs baseline:")
                for r in comparison.regressions():
                    print(f"   {r.game}.{r.metric}: {r.baseline} -> {r.current}")
                return 1
            print("OK: no regression beyond tolerance.")
            return 0
        finally:
            result.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tests.e2e.enrichment")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record", help="record the frozen scraping of the e2e games")
    p_rec.add_argument("--ids", default=",".join(map(str, DEFAULT_IDS)),
                       help="corpus id_product, comma-separated")
    p_rec.set_defaults(func=_cmd_record)

    p_run = sub.add_parser("run", help="ingest + scorecard + baseline diff (gate)")
    p_run.add_argument("--update-baseline", action="store_true",
                       help="rewrite baseline.json with the current scorecard")
    p_run.set_defaults(func=_cmd_run)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
