"""Chat endpoint — the conversational advisor.

`POST /chat`, one contract `{message, games, quick_replies}`, two paths (docs/chat.md):
- no `session_id` → Phase 4, stateless: one turn → hybrid retrieval → grounded LLM pitch.
  Unchanged, fully backward compatible.
- `session_id` present → Phase 5, stateful: the LangGraph (session memory keyed by the id,
  strategy routing, clicks-as-filters, model tiering) wrapping the same retrieve→pitch core.

The graph is built lazily on the first stateful request: stateless deployments never open the
checkpoint DB. The stateful path goes through TieredChat (docs/idee.md §Q): the pipeline graph
is the fallback tier, the primary slot is where the agentic engine will plug in.
"""

from fastapi import APIRouter

from app.chat.advisor import ChatAdvisor
from app.chat.models.request import ChatRequest
from app.chat.models.response import ChatResponse
from app.chat.tiered import TieredChat

router = APIRouter()
_advisor = ChatAdvisor()
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.chat.graph import ChatGraph  # lazy: only stateful traffic pays for it

        _engine = TieredChat(fallback=ChatGraph(advisor=_advisor))
    return _engine


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if req.session_id:
        return _get_engine().reply(req.message, choices=req.choices, k=req.k,
                                   session_id=req.session_id)
    return _advisor.reply(req.message, choices=req.choices, k=req.k)
