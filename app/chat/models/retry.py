from pydantic import BaseModel, Field


class RetryDecision(BaseModel):
    """Structured output of the piloted engine's retry step (docs/idee.md §Q, arm B).

    The model is INFORMED that its search returned nothing and chooses, explicitly: reformulate
    once (a new `query`) or give up honestly (`no_match=true` → the deterministic honest reply).
    This is what turns the no-match from "guessed off a k-sized list" into knowledge — the
    model saw the result count. Defaults make an empty/failed output a retry with no query,
    which the code treats as giving up.
    """

    no_match: bool = Field(
        default=False, description="true se la richiesta non è soddisfacibile a catalogo: "
                                   "meglio dirlo onestamente che forzare una proposta"
    )
    query: str = Field(
        default="", description="la nuova query riformulata, solo se vale la pena ritentare"
    )
