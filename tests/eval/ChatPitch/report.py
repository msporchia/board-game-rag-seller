"""PitchReport — scoring of the pitch eval (see eval_report.EvalReport)."""

from tests.eval.report.eval_report import EvalReport


class PitchReport(EvalReport):
    """Grounded-generation rates, plus every failed check as a readable per-case line.

    Headline: `fallback_rate` — the share of cases where pitch() degraded to the deterministic
    reply. The behavioral rates are computed over the records where the check is IN SCOPE
    (value not None): on a fallback the text comes from deterministic code, not the model, so
    the behavioral checks are out of scope there. The summary lists each failing case with the
    checks it failed — prompt tuning opens one case at a time (full record in `runs/last.json`).
    """

    prefix = "pitch"
    title = "ChatPitch — pitch()"
    measure = "grounded-generation rates"

    # (metric name, record key, scope shown in the summary); a tuning experiment that changes
    # how a reply is judged adds/overrides entries here, in the suite's own report class.
    rate_keys = (
        ("fallback_rate", "fallback", "all cases — lower is better"),
        ("games_within_k", "within_k", "non-fallback replies"),
        ("guided_asks_question", "asks_question", "non-fallback GUIDED"),
        ("quick_match_proposes", "proposes_enough", "non-fallback QUICK_MATCH, >=3 hits"),
        ("beginner_jargon_free", "jargon_free", "non-fallback beginner"),
    )

    def aggregate(self) -> dict:
        metrics: dict = {"n_cases": len(self.records)}
        for name, key, _scope in self.rate_keys:
            metrics[name] = self._rate(key)
        metrics["fallback_cases"] = [r["case"] for r in self.records if r["fallback"]]
        return metrics

    def _rate(self, key: str) -> dict:
        """{n, ok, rate} over the records where `key` is in scope (not None)."""
        vals = [r[key] for r in self.records if r.get(key) is not None]
        ok = sum(1 for v in vals if v)
        return {"n": len(vals), "ok": ok, "rate": round(ok / len(vals), 4) if vals else None}

    def sections(self) -> dict:
        """Failures first, grouped per strategy, each one self-contained: which checks failed,
        the customer request, the hits offered, and what the model actually replied (message,
        games, quick_replies) — enough to judge the case without rerunning."""
        failures: dict[str, list] = {}
        passes: dict[str, list] = {}
        for rec in self.records:
            failed = self._failed_checks(rec)
            if not failed:
                passes.setdefault(rec["strategy"], []).append(rec["case"])
                continue
            failures.setdefault(rec["strategy"], []).append({
                "case": rec["case"],
                "failed": failed,
                "expertise_level": rec.get("expertise_level"),
                "request": rec.get("request"),
                "hits": rec.get("hits"),
                "reply_message": rec.get("message"),
                "reply_games": rec.get("games"),
                "reply_quick_replies": rec.get("quick_replies"),
                "jargon_found": rec.get("jargon_found"),
                "note": rec.get("note"),
            })
        return {"failures": failures, "passes": passes}

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        lines = [f"  Cases: {metrics['n_cases']}", ""]
        for name, _key, scope in self.rate_keys:
            m = metrics[name]
            prev_rate = (prev or {}).get(name, {}).get("rate")
            if m["rate"] is None:
                lines.append(f"  {name:22s}    —     (no cases in scope: {scope})")
                continue
            lines.append(f"  {name:22s} {m['ok']:>2d}/{m['n']:<2d} "
                         f"{self.delta(m['rate'], prev_rate)}   [{scope}]")

        failures = [(r["case"], self._failed_checks(r)) for r in self.records]
        failures = [(case, failed) for case, failed in failures if failed]
        if failures:
            lines.append("")
            for case, failed in failures:
                lines.append(f"  ✗ {case}: {', '.join(failed)}")
        return lines

    def _failed_checks(self, rec: dict) -> list[str]:
        """The record's checks that are in scope and failed ('fallback' fails when True)."""
        failed = ["fallback"] if rec["fallback"] else []
        failed += [name for name, key, _scope in self.rate_keys
                   if key != "fallback" and rec.get(key) is False]
        return failed
