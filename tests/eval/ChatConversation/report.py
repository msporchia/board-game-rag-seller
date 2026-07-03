"""ConversationReport — scoring of the conversation eval (see eval_report.EvalReport)."""

import re
from pathlib import Path

from tests.eval.report.eval_report import EvalReport


class ConversationReport(EvalReport):
    """Whole-conversation pass rate, plus the per-aspect rates the cases probe.

    A case passes when every check IN SCOPE for it passed: its per-turn oracles
    (strategy/min_games/no_match), convergence (an accepted game recommended within the case's
    turn budget), final filters integrity, and the forced-proposal rule. Checks a case does not
    declare are out of scope (None) — each rate is averaged only over its own cases, like
    ChatPitch. `fallback_turn_rate` is informational across ALL turns: how often a real
    multi-turn session degrades to the deterministic reply.

    The report is ENGINE-TAGGED (docs/idee.md §Q): the model label carries the arm under eval
    and the metrics carry the cost block (LLM calls, Ollama tokens) — comparing two consecutive
    runs (pipeline, then piloted) reads as Δquality next to Δcost, the deciding number.
    """

    prefix = "conversation"
    title = "ChatConversation — full multi-turn sessions"
    measure = "whole-conversation pass rates"

    def __init__(self, runs_dir: Path, engine: str = "pipeline", model_label: str | None = None):
        super().__init__(runs_dir)
        self.engine = engine
        # Simulation runs (tests/eval/ChatConversation/simulation/) label the numbers with the
        # external responder instead of an Ollama model name; None preserves the original lookup.
        self._model_label_override = model_label

    def model(self) -> str:
        if self._model_label_override:
            return self._model_label_override
        from app.config import settings
        # The agent arm runs on the strong / tool-capable model (LLM_MODEL_STRONG); pipeline and
        # piloted run on llm_model. Label the numbers with the model that actually produced them.
        base = ((settings.llm_model_strong or settings.llm_model)
                if self.engine == "agent" else settings.llm_model)
        return f"{base} · engine={self.engine}"

    # (metric name, scope shown in the summary)
    rate_specs = (
        ("case_pass", "all conversations"),
        ("convergence", "cases with an accepted-games oracle"),
        ("turn_oracles", "declared per-turn checks"),
        ("filters_ok", "cases with a final-filters oracle"),
        ("proposal_ok", "cases with the forced-proposal oracle"),
    )

    def aggregate(self) -> dict:
        n_turns = sum(r["n_turns"] for r in self.records)
        fallback_turns = sum(r["fallback_turns"] for r in self.records)
        converged = [r for r in self.records if r["converged"] is not None]
        turns_to = [r["turns_to_converge"] for r in converged if r["turns_to_converge"]]
        checks = sum(r["n_turn_checks"] for r in self.records)
        check_failures = sum(len(r["turn_failures"]) for r in self.records)
        llm_calls = sum(r.get("llm_calls") or 0 for r in self.records)
        tokens = sum((r.get("tokens_in") or 0) + (r.get("tokens_out") or 0)
                     for r in self.records)
        return {
            "n_cases": len(self.records),
            "n_turns": n_turns,
            "cost": {
                "llm_calls": llm_calls,
                "llm_calls_per_turn": round(llm_calls / n_turns, 2) if n_turns else 0.0,
                "tokens_in": sum(r.get("tokens_in") or 0 for r in self.records),
                "tokens_out": sum(r.get("tokens_out") or 0 for r in self.records),
                "tokens_per_conversation": (round(tokens / len(self.records))
                                            if self.records else 0),
            },
            "case_pass": self._ratio([self._passed(r) for r in self.records]),
            "convergence": self._ratio([r["converged"] for r in converged]),
            "mean_turns_to_converge": (round(sum(turns_to) / len(turns_to), 2)
                                       if turns_to else None),
            "turn_oracles": {"n": checks, "ok": checks - check_failures,
                             "rate": (round((checks - check_failures) / checks, 4)
                                      if checks else None)},
            "filters_ok": self._ratio([r["filters_ok"] for r in self.records
                                       if r["filters_ok"] is not None]),
            "proposal_ok": self._ratio([r["proposal_ok"] for r in self.records
                                        if r["proposal_ok"] is not None]),
            "fallback_turn_rate": round(fallback_turns / n_turns, 4) if n_turns else 0.0,
            "failed_cases": [r["case"] for r in self.records if not self._passed(r)],
        }

    @staticmethod
    def _ratio(vals: list) -> dict:
        ok = sum(1 for v in vals if v)
        return {"n": len(vals), "ok": ok, "rate": round(ok / len(vals), 4) if vals else None}

    @staticmethod
    def _passed(rec: dict) -> bool:
        return (not rec["turn_failures"] and rec["converged"] is not False
                and rec["filters_ok"] is not False and rec["proposal_ok"] is not False)

    def headline(self, metrics: dict) -> str:
        conv = metrics["convergence"]["rate"]
        cost = metrics["cost"]
        return (f"case pass **{metrics['case_pass']['rate']:.3f}** · "
                f"{metrics['n_cases']} conversations / {metrics['n_turns']} turns "
                f"(convergence {'—' if conv is None else f'{conv:.3f}'}, "
                f"fallback/turn {metrics['fallback_turn_rate']:.3f}) · "
                f"{cost['llm_calls']} LLM calls / "
                f"{cost['tokens_in'] + cost['tokens_out']} tok")

    def sections(self) -> dict:
        """Failures first, each self-contained: which checks failed, the full trajectory as
        readable turn lines (strategy, escalation, fallback, games on the table, bot reply),
        and the oracle — enough to judge the conversation without rerunning."""
        failures = []
        passes = []
        for rec in self.records:
            if self._passed(rec):
                passes.append({
                    "case": rec["case"],
                    "converged turn": rec["turns_to_converge"],
                    "cost": self._case_cost(rec),
                    "trajectory": self._compact_trajectory(rec["trajectory"]),
                })
                continue
            failures.append({
                "case": rec["case"],
                "failed": self._failed_checks(rec),
                "cost": self._case_cost(rec),
                "trajectory": self._render_trajectory(rec["trajectory"]),
                "expected": rec.get("expected"),
                "final_filters": rec.get("final_filters"),
                "note": rec.get("note"),
            })
        return {"failures": failures, "passes": passes}

    @staticmethod
    def _case_cost(rec: dict) -> str:
        tokens = (rec.get("tokens_in") or 0) + (rec.get("tokens_out") or 0)
        return f"{rec.get('llm_calls') or 0} LLM calls / {tokens} tok"

    def _failed_checks(self, rec: dict) -> list[str]:
        failed = list(rec["turn_failures"])
        if rec["converged"] is False:
            failed.append(f"convergence (by turn {rec['by_turn']})")
        if rec["filters_ok"] is False:
            failed.append("final filters")
        if rec["proposal_ok"] is False:
            failed.append("forced proposal")
        return failed

    def _render_trajectory(self, trajectory: list[dict]) -> list[str]:
        lines = []
        for t in trajectory:
            clicks = f" + click {t['choices']}" if t["choices"] else ""
            games = ", ".join(self._short_name(n) for n in t["games"]) or "no games"
            lines.append(f"{t['turn']}. utente: {t['user']}{clicks}")
            # Piloted arm: the searches the loop actually ran (intent reformulation, retry).
            for s in t.get("searches") or []:
                flt = ", ".join(f"{k}={v}" for k, v in sorted(s["filters"].items())) or "none"
                ids = f" {s['hit_ids']}" if s.get("hit_ids") else ""
                lines.append(f"   search: «{s['query']}» [filters: {flt}] → "
                             f"{s['n_hits']} hits{ids}")
            lines.append(f"   [{t['strategy']}{self._marks(t)}] {games} — bot: {t['bot'][:160]}")
        return lines

    def _compact_trajectory(self, trajectory: list[dict]) -> list[str]:
        """One line per turn for the passes section: the ask, the routed strategy and the
        games on the table — the shape of a good conversation at a glance."""
        lines = []
        for t in trajectory:
            user = t["user"] if len(t["user"]) <= 58 else t["user"][:57] + "…"
            clicks = f" + click {t['choices']}" if t["choices"] else ""
            games = ", ".join(self._short_name(n) for n in t["games"]) or "no games"
            lines.append(f"{t['turn']}. «{user}»{clicks} → "
                         f"{t['strategy']}{self._marks(t)}: {games}")
        return lines

    @staticmethod
    def _cost_line(cost: dict, prev: dict | None) -> str:
        """LLM calls and tokens with the raw delta vs the previous run (often the other arm)."""

        def shown(key: str, value) -> str:
            if not prev or key not in prev:
                return f"{value}"
            return f"{value} (Δ {value - prev[key]:+d}, was: {prev[key]})"

        tokens = cost["tokens_in"] + cost["tokens_out"]
        prev_tokens = ((prev["tokens_in"] + prev["tokens_out"])
                       if prev and "tokens_in" in prev else None)
        tok = (f"{tokens}" if prev_tokens is None
               else f"{tokens} (Δ {tokens - prev_tokens:+d}, was: {prev_tokens})")
        return (f"  LLM calls: {shown('llm_calls', cost['llm_calls'])}   "
                f"({cost['llm_calls_per_turn']}/turn)   tokens: {tok}   "
                f"({cost['tokens_per_conversation']}/conversation)")

    @staticmethod
    def _marks(turn: dict) -> str:
        return ("".join([" ESC" if turn["escalate"] else "",
                         " FALLBACK" if turn["fallback"] else ""]))

    @staticmethod
    def _short_name(name: str) -> str:
        """Catalog names are full marketing titles ('Massive Darkness - Gioco Cooperativo
        Fantasy con…'); keep the part before the first dash/pipe separator."""
        return re.split(r"\s+[-|–]\s+", name)[0].strip()

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        lines = [f"  Conversations: {metrics['n_cases']}   turns: {metrics['n_turns']}   "
                 f"fallback/turn: {self.delta(metrics['fallback_turn_rate'], (prev or {}).get('fallback_turn_rate'))}",
                 self._cost_line(metrics["cost"], (prev or {}).get("cost")),
                 ""]
        for name, scope in self.rate_specs:
            m = metrics[name]
            prev_rate = (prev or {}).get(name, {}).get("rate")
            if m["rate"] is None:
                lines.append(f"  {name:18s}    —     (no cases in scope: {scope})")
                continue
            lines.append(f"  {name:18s} {m['ok']:>2d}/{m['n']:<2d} "
                         f"{self.delta(m['rate'], prev_rate)}   [{scope}]")
        if metrics["mean_turns_to_converge"] is not None:
            lines.append(f"  mean turns to converge: {metrics['mean_turns_to_converge']}")
        lines.append("")
        for rec in self.records:
            failed = self._failed_checks(rec)
            mark = "✓" if not failed else "✗"
            tail = f": {', '.join(failed)}" if failed else (
                f" (converged turn {rec['turns_to_converge']})"
                if rec["turns_to_converge"] else "")
            lines.append(f"  {mark} {rec['case']}{tail}")
        return lines
