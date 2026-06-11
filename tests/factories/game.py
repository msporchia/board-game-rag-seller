from app.models.game_doc import GameDoc


def make_game(**overrides) -> GameDoc:
    """Test GameDoc with sensible defaults; `overrides` overrides the DTO fields."""
    dto = {"id_product": 1, "name": "Test Game", "description": "Una descrizione di prova."}
    dto.update(overrides)
    return GameDoc.from_dto(dto)
