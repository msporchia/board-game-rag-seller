"""Chat endpoint — the conversational advisor (Phase 4, stateless).

`POST /chat`: one user turn → hybrid retrieval → grounded LLM pitch + quick replies, in the
structured `{message, games, quick_replies}` contract (docs/seller.md §7). Stateless for now:
session memory, strategy routing and model tiering are Phase 5 (docs/chat.md).
"""

from fastapi import APIRouter

from app.chat.advisor import ChatAdvisor
from app.chat.models import ChatRequest, ChatResponse

router = APIRouter()
_advisor = ChatAdvisor()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return _advisor.reply(req.message, choices=req.choices, k=req.k)
