"""SimulationRunner — plays one ChatConversation eval run with every LLM role answered by an
EXTERNAL responder instead of Ollama (the "strong-model simulation" harness: measuring "8B local
model vs Claude-simulated" on the SAME eval cases with the SAME oracle).

Builds the SAME engine (pipeline / piloted / agent) over the SAME frozen corpus and the SAME
`fixtures/conversation_cases.json` cases, scored by the SAME `ConversationDriver` +
`ConversationReport` the real eval uses (../conversation_driver.py, ../report.py) — only the LLM
roles are swapped for `FileExchangeLLM` / `FileExchangeAgentLLM` (file_exchange_llm.py,
file_exchange_agent_llm.py), which round-trip every call through
`<exchange-dir>/{pending,replies,rejected,answered}` for a human (or another model) to answer by
hand. See those two classes' module docstrings, and `exchange_transport.py`, for the exact
request/reply JSON shapes and the reject-and-retry protocol.

Persists `tests/eval/ChatConversation/runs/sim-<engine>.json` — NEVER `runs/last.json` (that
file is the 8B baseline `compare.py` diffs the simulation against).

    docker compose exec seller-api python -m tests.eval.ChatConversation.simulation.run \\
        --engine pipeline --exchange-dir /app/data/exchange --case carcassonne-cliente-deciso

Responder protocol, from the host (the exchange dir is `./data/exchange/<engine>/` bind-mounted
at `/app/data/exchange/<engine>/` — same files, either side): watch `pending/`, for each file
write the matching `replies/<seq>.json` per its `reply_schema`; an invalid reply is moved to
`rejected/` with a sibling `.error.txt` and the SAME `replies/<seq>.json` path is polled again,
so just re-write it. A fulfilled request's pending file moves itself to `answered/` — nothing to
track by hand, answer everything currently in `pending/`.
"""

import argparse
import json
import sys
from pathlib import Path

from tests.eval.ChatConversation.conversation_driver import ConversationDriver
from tests.eval.ChatConversation.report import ConversationReport
from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.sim_engine_builder import SimEngineBuilder

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "conversation_cases.json"
RUNS = Path(__file__).resolve().parents[1] / "runs"


class SimulationRunner:
    def run(self, argv: list[str]) -> None:
        args = self._parse(argv)
        cases = self._select_cases(args.case)
        exchange = ExchangeDir(Path(args.exchange_dir) / args.engine)
        builder = SimEngineBuilder(exchange, timeout=args.timeout)
        report = ConversationReport(
            RUNS, engine=args.engine,
            model_label=f"EXTERNAL RESPONDER (simulated) · engine={args.engine}")

        print(f"[sim] engine={args.engine}  exchange dir={exchange.root}  "
             f"cases={len(cases)}  timeout={args.timeout:.0f}s")
        with builder.build(args.engine) as engine:
            for case in cases:
                print(f"[sim] case «{case['id']}» — {len(case['turns'])} turn(s), "
                     f"waiting on {exchange.pending} ...")
                record = ConversationDriver().run(engine, case, builder.usage)
                report.record(record)
                verdict = "PASS" if self._passed(record) else "FAIL"
                print(f"[sim] case «{case['id']}» → {verdict}")

        out_name = f"sim-{args.engine}"
        report.finish(0, out_name=out_name, persist_last=False, write_markdown=False)
        print(f"[sim] wrote {RUNS / (out_name + '.json')}")

    @staticmethod
    def _passed(rec: dict) -> bool:
        return (not rec["turn_failures"] and rec["converged"] is not False
                and rec["filters_ok"] is not False and rec["proposal_ok"] is not False)

    @staticmethod
    def _select_cases(ids: list[str] | None) -> list[dict]:
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if not ids:
            return cases
        wanted = set(ids)
        selected = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in selected}
        if missing:
            sys.exit(f"unknown case id(s): {sorted(missing)}")
        return selected

    @staticmethod
    def _parse(argv: list[str]) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description=__doc__,
                                        formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("--engine", required=True, choices=["pipeline", "piloted", "agent"])
        parser.add_argument("--exchange-dir", required=True,
                            help="e.g. /app/data/exchange (the container path of the host's "
                                 "./data/exchange, bind-mounted by docker-compose.yml)")
        parser.add_argument("--case", action="append", default=None,
                            help="case id to run (repeatable); default: every case")
        parser.add_argument("--timeout", type=float, default=900.0,
                            help="seconds to wait for each reply before raising (default 900)")
        return parser.parse_args(argv)


if __name__ == "__main__":
    SimulationRunner().run(sys.argv[1:])
