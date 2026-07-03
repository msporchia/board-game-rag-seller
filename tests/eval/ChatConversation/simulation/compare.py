"""ArmComparator — reads the 8B baseline (`runs/last.json`) and one or more simulation runs
(`runs/sim-*.json`) and prints a Markdown table: per-case pass/fail for each arm, plus the
aggregate case-pass rate, turn count and LLM-call cost — turning "on a stronger model it flies"
into a measured number.

    docker compose exec seller-api python -m tests.eval.ChatConversation.simulation.compare
    # or pass explicit run files:
    docker compose exec seller-api python -m tests.eval.ChatConversation.simulation.compare \\
        tests/eval/ChatConversation/runs/last.json tests/eval/ChatConversation/runs/sim-agent.json
"""

import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "runs"


class ArmComparator:
    def run(self, argv: list[str]) -> None:
        paths = [Path(p) for p in argv] if argv else self._default_paths()
        arms = [self._load(p) for p in paths if p.exists()]
        for missing in (p for p in paths if not p.exists()):
            print(f"(skipped, not found: {missing})", file=sys.stderr)
        if not arms:
            sys.exit("no run files found to compare")
        print(self._render(arms))

    @staticmethod
    def _default_paths() -> list[Path]:
        return [RUNS / "last.json", *sorted(RUNS.glob("sim-*.json"))]

    @staticmethod
    def _load(path: Path) -> dict:
        run = json.loads(path.read_text(encoding="utf-8"))
        return {"label": path.stem, "model": run.get("model", "?"),
               "metrics": run.get("metrics", {}),
               "records": {r["case"]: r for r in run.get("records", [])}}

    @staticmethod
    def _passed(rec: dict) -> bool:
        return (not rec["turn_failures"] and rec["converged"] is not False
                and rec.get("filters_ok") is not False and rec.get("proposal_ok") is not False)

    def _render(self, arms: list[dict]) -> str:
        case_ids = sorted({cid for arm in arms for cid in arm["records"]})
        lines = ["## ChatConversation — arm comparison", "",
                "| case | " + " | ".join(arm["label"] for arm in arms) + " |",
                "|---|" + "---|" * len(arms)]
        for cid in case_ids:
            row = [cid]
            for arm in arms:
                rec = arm["records"].get(cid)
                row.append("—" if rec is None else ("PASS" if self._passed(rec) else "FAIL"))
            lines.append("| " + " | ".join(row) + " |")

        lines += ["", "| arm | model | case pass | turns | LLM calls |",
                 "|---|---|---|---|---|"]
        for arm in arms:
            m = arm["metrics"]
            case_pass = m.get("case_pass", {})
            cost = m.get("cost", {})
            lines.append(
                f"| {arm['label']} | {arm['model']} | "
                f"{case_pass.get('ok', '?')}/{case_pass.get('n', '?')} "
                f"({case_pass.get('rate', '?')}) | {m.get('n_turns', '?')} | "
                f"{cost.get('llm_calls', '?')} |")
        return "\n".join(lines)


if __name__ == "__main__":
    ArmComparator().run(sys.argv[1:])
