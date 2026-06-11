from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="the user's free-text turn")
    # Quick-reply clicks. Phase 4 (stateless) appends them to the retrieval query; Phase 5
    # (with `session_id`) parses them into real hybrid-search filters merged into the session.
    choices: list[str] = []
    k: int = Field(5, ge=1, le=20)
    # Present → stateful Phase 5 path (LangGraph with session memory, keyed by this id).
    # Absent → the original stateless Phase 4 behavior, unchanged.
    session_id: str | None = None
