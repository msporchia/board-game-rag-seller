from typing import Literal

from pydantic import BaseModel, Field


class TurnAnalysis(BaseModel):
    """Structured output of the analyze node: one LLM call per turn, reading the user.

    The first four fields are the user-analysis dimensions from docs/note.md; the last three are
    the model-tiering escalation contract (the analyzer proposes, deterministic code and the
    generate step act on it). Defaults are the safe middle ground, also used when the analyzer
    LLM fails — the conversation must never 500 because the analysis did.
    """

    enthusiasm: Literal["low", "medium", "high"] = "medium"
    decisiveness: Literal["undecided", "moderate", "decided"] = "undecided"
    expertise_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    reply_style: Literal["short", "long"] = "short"

    # Escalation contract (docs/note.md "Model tiering"): when True, the generate step switches
    # to the strong model (settings.llm_model_strong). Reason and confidence are logged.
    escalate: bool = False
    escalation_reason: str = ""
    confidence: float = Field(0.5, ge=0.0, le=1.0)
