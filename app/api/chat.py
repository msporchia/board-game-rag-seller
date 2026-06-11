"""Chat endpoint — the conversational advisor.

`POST /chat`, one contract `{message, games, quick_replies}`, two paths (docs/chat.md):
- no `session_id` → Phase 4, stateless: one turn → hybrid retrieval → grounded LLM pitch.
  Unchanged, fully backward compatible.
- `session_id` present → Phase 5, stateful: the LangGraph (session memory keyed by the id,
  strategy routing, clicks-as-filters, model tiering) wrapping the same retrieve→pitch core.

The graph is built lazily on the first stateful request: stateless deployments never open the
checkpoint DB.
"""

from fastapi import APIRouter

from app.chat.advisor import ChatAdvisor
from app.chat.models.request import ChatRequest
from app.chat.models.response import ChatResponse

router = APIRouter()
_advisor = ChatAdvisor()
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from app.chat.graph import ChatGraph  # lazy: only stateful traffic pays for it

        _graph = ChatGraph(advisor=_advisor)
    return _graph


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if req.session_id:
        return _get_graph().reply(req.message, choices=req.choices, k=req.k,
                                  session_id=req.session_id)
    return _advisor.reply(req.message, choices=req.choices, k=req.k)
