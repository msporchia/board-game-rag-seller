"""Serializer: GameDoc → LangChain Document. Thin, NO composition.

- page_content = `embed_text` (produced by a pipeline compose step);
- metadata = structured payload (the `enriched` fields for hybrid-search filters).
"""

from langchain_core.documents import Document

from app.models import GameDoc


class DocumentSerializer:
    def to_document(self, game: GameDoc) -> Document:
        # embed_text is produced by a compose step; minimal safety fallback
        text = game.embed_text or game.enriched.name
        return Document(page_content=text, metadata=self.build_payload(game))

    def build_payload(self, game: GameDoc) -> dict:
        e = game.enriched
        return {
            "id_product": e.id_product,
            "name": e.name,
            "players": e.players,
            "players_display": e.players_display,
            "duration_min": e.duration_min,
            "age_min": e.age_min,
            "complexity": e.complexity,
            "complexity_level": e.complexity_level,
            "year": e.year,
            "internal_rating": e.internal_rating,
            "tags": e.tags,
            "is_expansion": e.is_expansion,
            "categoria": e.categoria,
            "marca": e.marca,
            "image": e.image,
            "content_hash": e.content_hash,
        }
