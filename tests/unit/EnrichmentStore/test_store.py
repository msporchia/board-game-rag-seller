"""EnrichmentStore (in-memory SQLite, no network): curated record + page cache + provenance."""

from app.ingestion.enricher import RuleComposeEnricher
from tests.factories import make_game


class TestEnrichmentStore:
    def test_save_and_get_game_roundtrip(self, store):
        g = RuleComposeEnricher().enrich(
            make_game(id_product=7, content_hash="h1", tags=["Coop"], players=[1, 2, 3])
        )
        g = g.model_copy(update={"missing_info": ["durata"]})
        store.save_game(g)

        back = store.get_game(7)
        assert back is not None
        assert back.original.model_dump() == g.original.model_dump()
        assert back.enriched.model_dump() == g.enriched.model_dump()
        assert back.embed_text == g.embed_text
        assert back.missing_info == ["durata"]

    def test_save_game_is_upsert(self, store):
        store.save_game(make_game(id_product=1, content_hash="a"))
        store.save_game(make_game(id_product=1, content_hash="b"))
        assert store.content_hash(1) == "b"
        assert store.get_game(1) is not None

    def test_get_missing_game_returns_none(self, store):
        assert store.get_game(999) is None
        assert store.content_hash(999) is None

    def test_page_cache_roundtrip(self, store):
        assert store.get_page("https://x.it/a") is None
        store.save_page("https://x.it/a", 200, "testo pulito")
        assert store.get_page("https://x.it/a") == "testo pulito"
        store.save_page("https://x.it/a", 200, "aggiornato")  # upsert
        assert store.get_page("https://x.it/a") == "aggiornato"

    def test_extractions_and_scoreboard(self, store):
        store.save_extraction(1, "tema", "Toscana", "ambientato in Toscana",
                              "https://goblins.net/x", "goblins.net", "llama3.1")
        store.save_extraction(1, "meccaniche", "piazzamento", "worker placement",
                              "https://goblins.net/y", "goblins.net", "llama3.1")
        store.save_extraction(2, "tema", "spazio", "ambientato nello spazio",
                              "https://balenaludens.it/z", "balenaludens.it", "llama3.1")

        assert len(store.get_extractions(1)) == 2
        board = store.source_scoreboard()
        assert board[0] == {"source_domain": "goblins.net", "n": 2}
        assert {"source_domain": "balenaludens.it", "n": 1} in board
