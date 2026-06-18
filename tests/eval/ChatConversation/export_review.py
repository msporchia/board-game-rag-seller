"""Export a ChatConversation run as a self-contained REVIEW bundle for MANUAL / stronger-model review.

The rule-based rates (RESULTS.md) say HOW OFTEN the seller converged; they cannot judge whether a
pick was apt, whether the model invented a constraint the customer never stated, whether the tone
is right, or whether it gave up too early with an honest-but-lazy "no match". This command lays a
whole run open — every search the agent ran, every reply it wrote, and the games that were actually
available — next to the goal and an explicit rubric, so a human (or a more powerful model) can say
"ok, but what did it ACTUALLY produce?" without rerunning anything. Nothing behind the scenes is
hidden: the rate is the headline, this is the footnotes.

    docker compose exec seller-api python -m tests.eval.ChatConversation.export_review
    # reads runs/last.json (or a path passed as argv[1]); writes tests/eval/ChatConversation/REVIEW.md
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
CORPUS = HERE.parents[1] / "fixtures" / "suites" / "core" / "games_enriched.json"
OUT = HERE / "REVIEW.md"

_OBJECTIVE = """The seller is a board-game shop assistant. For every customer turn it must:
1. **Ground** every recommendation — only games that are really in the catalog (enforced in code);
   it may never invent a title, and if a named title is absent it says so and offers a real one.
2. **Pick the RIGHT games** for what the customer actually asked (theme, mechanics, players, mood).
3. **Sell them** warmly and honestly — persuasive prose, no invented prices/stock.
4. **Ask a smart follow-up** when the ask is still vague, instead of guessing blindly.
5. Give an **honest "no match"** when nothing fits — but only after genuinely trying, not as an
   easy way out.

The `agent` engine does all of this by driving a `search_catalog` tool ITSELF with a small local
model — we do NOT pilot it step by step. That is the whole point of measuring it: to see whether
raw tool-use by a cheap model reaches the bar, rather than assuming it does."""

_RUBRIC = """The rates below (convergence, etc.) are RULE-based and only check whether an accepted
game was eventually shown. They are blind to the things that actually decide quality — judge THOSE
here, per conversation:

- **Aptness** — are the recommended games a genuinely good fit, or just thematically nearby?
- **Invented constraints** — did it add a filter the customer never stated (e.g. `players=4` from
  "three or four", an `age`/`duration` cap out of nowhere)? Over-constraining silently drops good
  games and causes false "no match".
- **Persistence** — did it give up with a "no match" when it should have searched differently?
- **Personality / tone** — warm, helpful, natural Italian? Any awkward or garbled phrasing?
- **Honesty** — every shown game is real (grounding is enforced) — confirm nothing odd slipped, and
  that absent titles are handled gracefully.

Note: the model is stochastic, so a single run is a sample, not a verdict — read the trajectories,
not just the pass/fail mark."""


def _short(name: str) -> str:
    return re.split(r"\s+[-|–]\s+", name or "")[0].strip()


def _load_catalog() -> dict[int, dict]:
    games = json.loads(CORPUS.read_text(encoding="utf-8"))
    catalog = {}
    for g in games:
        original = g.get("original") or {}
        enriched = g.get("enriched") or original
        idp = original.get("id_product") or g.get("id_product")
        if idp is None:
            continue
        players = enriched.get("players") or []
        catalog[idp] = {
            "name": _short(enriched.get("name") or original.get("name") or f"id {idp}"),
            "players": (f"{min(players)}-{max(players)}" if players else "?"),
            "duration": enriched.get("duration_min") or "?",
            "tags": ", ".join((enriched.get("tags") or [])[:6]),
        }
    return catalog


def _passed(rec: dict) -> bool:
    return (not rec["turn_failures"] and rec["converged"] is not False
            and rec.get("filters_ok") is not False and rec.get("proposal_ok") is not False)


def _verdict(rec: dict) -> str:
    if _passed(rec):
        tt = rec.get("turns_to_converge")
        return f"PASS — converged at turn {tt}" if tt else "PASS"
    fails = list(rec["turn_failures"])
    if rec["converged"] is False:
        fails.append(f"no accepted game by turn {rec.get('by_turn')}")
    return "FAIL — " + ", ".join(fails)


def _names(catalog: dict, ids: list[int]) -> str:
    return ", ".join(f"`{i}` {catalog.get(i, {}).get('name', '?')}" for i in ids) or "—"


def _render_case(rec: dict, catalog: dict) -> list[str]:
    exp = rec.get("expected") or {}
    lines = [f"### {rec['case']} — {_verdict(rec)}", ""]
    lines.append(f"**Goal of this case:** {rec.get('note', '')}")
    if exp.get("accept_ids"):
        by = exp.get("by_turn") or rec["n_turns"]
        lines.append(f"**Accepted games (oracle):** {_names(catalog, exp['accept_ids'])} — "
                     f"any of these shown by turn {by} counts as converged.")
    lines.append(f"**Cost:** {rec.get('llm_calls') or 0} LLM calls / "
                 f"{(rec.get('tokens_in') or 0) + (rec.get('tokens_out') or 0)} tokens")
    lines.append("")
    for t in rec["trajectory"]:
        clicks = f"  ·  click: {t['choices']}" if t["choices"] else ""
        lines.append(f"**Turn {t['turn']}** — 🧑 *{t['user']}*{clicks}")
        for s in t.get("searches") or []:
            flt = s.get("filters") or {}
            hit_names = ", ".join(_short(catalog.get(i, {}).get("name", str(i)))
                                  for i in (s.get("hit_ids") or []))
            lines.append(f"- 🔎 searched «{s['query']}» — filters `{flt or '∅'}` → "
                         f"{s['n_hits']} hits: {hit_names or '—'}")
        on_table = ", ".join(_short(n) for n in t["games"]) or "(none)"
        fb = " · ⚠️ deterministic fallback" if t.get("fallback") else ""
        lines.append(f"- 🃏 on the table: **{on_table}**{fb}")
        lines.append(f"- 🤖 {t['bot']}")
        lines.append("")
    lines.append("> _Reviewer notes:_ ")
    lines.append("")
    return lines


def main(argv: list[str]) -> None:
    run_path = Path(argv[1]) if len(argv) > 1 else (RUNS / "last.json")
    if not run_path.exists():
        sys.exit(f"no run file at {run_path} — run the eval first "
                 "(docker compose exec -e CHAT_ENGINE=agent ... pytest tests/eval/ChatConversation)")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    records = run.get("records")
    if not records:
        sys.exit("run file has no `records` (re-run the eval after this change persists them)")
    catalog = _load_catalog()
    m = run["metrics"]
    conv = m["convergence"]["rate"]

    out = [
        "<!-- Generated by tests/eval/ChatConversation/export_review.py — regenerate, do not hand-edit. -->",
        "# ChatConversation — review bundle (what the seller actually produced)",
        "",
        f"**Run:** `{run['model']}` · session `{run['session']}` · "
        f"{m['n_cases']} conversations / {m['n_turns']} turns · "
        f"case pass **{m['case_pass']['rate']:.3f}** · "
        f"convergence {'—' if conv is None else f'{conv:.3f}'} · "
        f"{m['cost']['llm_calls']} LLM calls / "
        f"{m['cost']['tokens_in'] + m['cost']['tokens_out']} tokens.",
        "",
        "## The goal", "", _OBJECTIVE, "",
        "## What to judge (the rubric the rates don't capture)", "", _RUBRIC, "",
        "## How to read each conversation", "",
        "For every turn: the customer's message (🧑), what the agent **searched** for (🔎 — the "
        "query it wrote, the structured filters it chose, the games that came back), the games it "
        "put **on the table** (🃏), and its full **reply** (🤖). Then the oracle (which games we'd "
        "accept, and why) and the verdict.", "",
        "---", "",
        "## Conversations", "",
    ]
    fixture_order = [r for r in records if not _passed(r)] + [r for r in records if _passed(r)]
    for rec in fixture_order:
        out += _render_case(rec, catalog)
        out += ["---", ""]

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT} ({len(fixture_order)} conversations, "
          f"{sum(1 for r in records if not _passed(r))} need attention first)")


if __name__ == "__main__":
    main(sys.argv)
