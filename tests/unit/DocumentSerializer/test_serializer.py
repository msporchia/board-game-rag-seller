"""DocumentSerializer: GameDoc → Document (page_content=embed_text, payload=enriched)."""

from app.ingestion.enricher import RuleComposeEnricher
from app.ingestion.serializer import DocumentSerializer
from tests.factories import make_game


class TestDocumentSerializer:
    def test_payload_comes_from_enriched(self):
        g = make_game(id_product=7, tags=["A"], duration_min=30)
        doc = DocumentSerializer().to_document(g)
        assert doc.metadata["id_product"] == 7
        assert doc.metadata["tags"] == ["A"]
        assert doc.metadata["duration_min"] == 30

    def test_page_content_is_embed_text(self):
        g = RuleComposeEnricher().enrich(make_game(name="Avel"))
        doc = DocumentSerializer().to_document(g)
        assert doc.page_content == g.embed_text

    def test_page_content_fallback_when_no_embed_text(self):
        g = make_game(name="Avel")  # no compose has run → embed_text None
        doc = DocumentSerializer().to_document(g)
        assert doc.page_content == "Avel"
