"""Manual runner (like try_web.py): record REAL chat sessions against the production index.

Runs `AgenticChat` in-process — not through HTTP — so every turn captures what the API response
cannot show: the searches the agent actually ran (`last_turn_searches`: query, filters, n_hits).
That per-turn search log is the "what is happening under the hood" layer of the live-session
showcase pages; the outcome is NOT piloted — whatever the seller does lands in the record.

    docker compose exec seller-api python -m tests.record_live_session --session coppia-serale
    docker compose exec seller-api python -m tests.record_live_session --all

Output: data/live-sessions/<name>.json (gitignored, like every runtime artifact in data/).
"""

import argparse
import json
from pathlib import Path

from app.chat.advisor import ChatAdvisor
from app.chat.agentic import AgenticChat

OUT_DIR = Path("/app/data/live-sessions")

# Four customer archetypes, in natural Italian (catalog language by design — see the README
# note on why the data and prompts are Italian). One list of turns per session.
SESSIONS = {
    # the couple: vague opener → constraint → the cooperative ask → widen the group
    "coppia-serale": [
        "ciao! cerco un gioco da regalare a una coppia di amici: giocano spesso in due la sera dopo cena",
        "sì, gli piace la strategia ma niente partite infinite, direi massimo un'ora",
        "ah, dimenticavo: adorano i giochi cooperativi, dove si vince o si perde insieme. c'è qualcosa di cooperativo che funzioni bene in due?",
        "perfetto! e se invece volessi qualcosa di cooperativo per quando invitano altri amici, tipo in cinque?",
    ],
    # the decided customer: precise title + purchase intent, then an adjacent ask
    "cliente-deciso": [
        "buongiorno, avete Carcassonne? vorrei regalarlo a mia sorella, mi serve per stasera",
        "perfetto! e c'è qualcosa di simile da affiancare al regalo, sempre di piazzamento tessere ma un po' più moderno?",
    ],
    # the birthday gift: age constraint → siblings play together → time cap
    "regalo-bambino": [
        "cerco un regalo per il compleanno di mio figlio, compie 8 anni",
        "bello! gioca spesso con la sorella più piccola, meglio qualcosa che possano fare insieme senza litigare",
        "l'ideale sarebbe una cosa da mezz'oretta, non di più",
    ],
    # the expert group converging on a specific game without naming it
    "esperti-fantascienza": [
        "siamo un gruppo di giocatori esperti e cerchiamo un titolo impegnativo per le nostre serate",
        "il tema che ci attira di più è la fantascienza, meglio se gestionale",
        "ci piacciono i giochi dove costruisci un motore di carte e risorse, tipo rendere abitabile un pianeta",
    ],
}


class LiveSessionRecorder:
    """Drives one scripted session through the real agent engine and captures every layer:
    the message, the searches the agent ran, the grounded hits, and the reply.

    With `exchange_dir` set, every LLM role (tool loop + pitch) is played by an external
    responder through the file-exchange harness instead of the local Ollama model — the
    "frontier tier" recording: same engine, same live index, same customer script; only the
    model at the wheel changes."""

    def __init__(self, exchange_dir: str | None = None, timeout: float = 3600.0):
        if exchange_dir:
            from pathlib import Path as _Path

            from app.chat.models.reply import ChatReply
            from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
            from tests.eval.ChatConversation.simulation.file_exchange_agent_llm import (
                FileExchangeAgentLLM)
            from tests.eval.ChatConversation.simulation.file_exchange_llm import FileExchangeLLM

            exchange = ExchangeDir(_Path(exchange_dir))
            advisor = ChatAdvisor(llm=FileExchangeLLM(exchange, "pitch", ChatReply,
                                                      timeout=timeout))
            self.engine = AgenticChat(advisor=advisor,
                                      llm=FileExchangeAgentLLM(exchange, timeout=timeout))
            self.model = "external responder (file exchange)"
        else:
            self.engine = AgenticChat(advisor=ChatAdvisor())
            self.model = None

    def record(self, name: str, turns: list[str]) -> dict:
        record = {"session": name, "engine": "agent", "turns": []}
        if self.model:
            record["model"] = self.model
        for i, message in enumerate(turns, 1):
            response = self.engine.reply(message, session_id=name)
            searches = [dict(s) for s in self.engine.last_turn_searches]
            games = [{
                "name": g.name, "players_display": g.players_display,
                "duration_min": g.duration_min, "cooperative": g.cooperative,
            } for g in (response.games or [])]
            record["turns"].append({
                "turn": i, "user": message, "searches": searches, "games": games,
                "reply": response.message, "quick_replies": response.quick_replies,
            })
            print(f"  T{i} 🔎 {[(s.get('query'), s.get('filters'), s.get('n_hits')) for s in searches]}")
            print(f"     🃏 {[g['name'][:40] for g in games]}")
        return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=list(SESSIONS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--exchange", metavar="DIR",
                    help="record with an external responder through the file-exchange harness "
                         "(the frontier-tier take) instead of the local Ollama model")
    ap.add_argument("--suffix", default="",
                    help="output filename suffix, e.g. '-frontier' → <name>-frontier.json")
    ap.add_argument("--timeout", type=float, default=3600.0)
    args = ap.parse_args()
    names = list(SESSIONS) if args.all else [args.session or "coppia-serale"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    recorder = LiveSessionRecorder(exchange_dir=args.exchange, timeout=args.timeout)
    for name in names:
        print(f"=== {name}")
        record = recorder.record(name, SESSIONS[name])
        out = OUT_DIR / f"{name}{args.suffix}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"  saved {out}")


if __name__ == "__main__":
    main()
