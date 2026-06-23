from pydantic import BaseModel, Field


class SearchIntent(BaseModel):
    """Structured output of the piloted engine's intent step (docs/idee.md §Q, arm B).

    The model expresses WHAT it would recommend; the code turns that into the retrieval call.
    `query` is the model's own reformulation in catalog language (the generate-then-retrieve /
    HyDE family) — it replaces the user's verbatim text as the search query. The constraint
    fields are the structured side-channel that keeps the 8B reformulation from losing the
    user's hard requirements: the code maps them onto SearchFilters (`to_filters_spec`), and
    click-derived session filters always override them on the same dimension — the model
    proposes, the code disposes.
    """

    query: str = Field(
        default="", description="riformulazione nel linguaggio del catalogo del gioco ideale "
                                "da consigliare: SOLO tema, meccaniche, tipo di esperienza, per "
                                "chi è. NON inserire qui i vincoli numerici (numero di giocatori, "
                                "durata, età): vanno nei campi appositi, perché la ricerca "
                                "semantica non li recepisce in modo affidabile — li applica un "
                                "filtro esatto. Es. NON 'gioco cooperativo per 2 persone' ma "
                                "'gioco cooperativo, si vince e si perde insieme' (+ players=2)."
    )
    players: int | None = Field(
        default=None, description="numero di giocatori dichiarato dal cliente, se presente. Il "
                                  "vincolo va QUI come intero, non nel testo della query"
    )
    max_minutes: int | None = Field(
        default=None, description="durata massima in minuti dichiarata dal cliente, se presente. "
                                  "QUI come intero (es. 60), non nel testo della query"
    )
    youngest_player_age: int | None = Field(
        default=None, description="età in anni del giocatore più giovane, se dichiarata. QUI come "
                                  "intero, non nel testo della query"
    )
    cooperative: bool | None = Field(
        default=None, description="modalità richiesta dal cliente, come vincolo netto (non nella "
                                  "query): True se chiede un gioco COOPERATIVO (si gioca tutti "
                                  "insieme contro il gioco), False se chiede esplicitamente un "
                                  "gioco COMPETITIVO (uno contro l'altro). Lascia null se non "
                                  "esprime una preferenza — non dedurla dal tono."
    )

    def to_filters_spec(self) -> dict:
        """The proposed constraints as a `SearchFilters.from_dict` spec fragment.

        Nonsense values (zero/negative) are dropped here — the disposing side of "the model
        proposes, the code disposes". Age maps to `age.max`: a game suits an N-year-old when
        its minimum age is <= N (same convention as the quick-reply parser).
        """
        spec: dict = {}
        if self.players and self.players >= 1:
            spec["players"] = {"vals": [self.players]}
        if self.max_minutes and self.max_minutes > 0:
            spec["duration"] = {"max": self.max_minutes}
        if self.youngest_player_age and self.youngest_player_age > 0:
            spec["age"] = {"max": self.youngest_player_age}
        if self.cooperative is not None:  # True → cooperative, False → competitive (SEL-142)
            spec["cooperative"] = {"val": self.cooperative}
        return spec
