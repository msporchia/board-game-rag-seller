"""Chat endpoint — the conversational advisor.

`POST /chat`, one contract `{message, games, quick_replies}`, two paths (docs/chat.md):
- no `session_id` → Phase 4, stateless: one turn → hybrid retrieval → grounded LLM pitch.
  Unchanged, fully backward compatible.
- `session_id` present → Phase 5, stateful, behind the engine selector (docs/idee.md §Q):
  `CHAT_ENGINE` picks the default arm (`pipeline` = the decomposed graph, `piloted` = arm B,
  the code-piloted agent loop) and `ChatRequest.engine` overrides it per request. Either way
  the turn goes through TieredChat: the selected arm is the primary that MAY fail, the
  pipeline graph is the fallback that must not — both share ONE checkpointer, so a degraded
  turn continues the SAME session state (ChatState is the lingua franca).

Engines are built lazily on the first stateful request: stateless deployments never open the
checkpoint DB.
"""

from fastapi import APIRouter

from app.chat.advisor import ChatAdvisor
from app.chat.models.request import ChatRequest
from app.chat.models.response import ChatResponse
from app.chat.tiered import TieredChat
from app.config import settings

router = APIRouter()
_advisor = ChatAdvisor()
_engines: dict[str, TieredChat] = {}
_graph = None         # the pipeline ChatGraph: the `pipeline` engine AND every fallback tier
_checkpointer = None  # shared by all engines: one session store, whichever arm serves a turn


def _get_engine(name: str) -> TieredChat:
    """The TieredChat for one engine name, built lazily and cached per process.

    Unknown names fall back to the pipeline — a config typo must degrade, never 500.
    """
    global _graph, _checkpointer
    name = name if name in ("pipeline", "piloted") else "pipeline"
    if name not in _engines:
        if _graph is None:
            from app.chat.checkpointer import sqlite_checkpointer  # lazy: stateful traffic only
            from app.chat.graph import ChatGraph

            _checkpointer = sqlite_checkpointer()
            _graph = ChatGraph(advisor=_advisor, checkpointer=_checkpointer)
        if name == "piloted":
            from app.chat.piloted import PilotedChat

            _engines["piloted"] = TieredChat(
                primary=PilotedChat(advisor=_advisor, checkpointer=_checkpointer),
                fallback=_graph)
        else:
            _engines["pipeline"] = TieredChat(fallback=_graph)
    return _engines[name]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if req.session_id:
        engine = _get_engine(req.engine or settings.chat_engine)
        return engine.reply(req.message, choices=req.choices, k=req.k,
                            session_id=req.session_id)
    return _advisor.reply(req.message, choices=req.choices, k=req.k)
