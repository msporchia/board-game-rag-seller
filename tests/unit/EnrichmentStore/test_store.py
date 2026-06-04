"""EnrichmentStore (in-memory SQLite, no network): curated record + page cache + provenance."""

import sqlite3

from app.core.enrichment_store import EnrichmentStore
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

    def test_extracted_roundtrip(self, store):
        """`extracted` (curator + web facts) is part of the system-of-record: it must survive
        the save/get round-trip, so an incremental re-ingest can skip re-deriving it."""
        g = make_game(id_product=8).model_copy(update={
            "extracted": {"ambientazione/tema": "Toscana", "meccaniche principali": ["piazzamento"]},
        })
        store.save_game(g)
        assert store.get_game(8).extracted == g.extracted

    def test_extracted_defaults_to_empty_dict(self, store):
        """A game saved without extractions reads back as an empty dict, never None/null."""
        store.save_game(make_game(id_product=9))
        assert store.get_game(9).extracted == {}

    def test_migration_adds_extracted_to_legacy_db(self, tmp_path):
        """An existing DB created before the `extracted` column must keep working: opening it
        migrates additively and old rows read back with an empty `extracted`."""
        db = str(tmp_path / "legacy.db")
        legacy = sqlite3.connect(db)
        legacy.executescript("""
            CREATE TABLE products (
                id_product INTEGER PRIMARY KEY, content_hash TEXT, name TEXT,
                original_json TEXT NOT NULL, enriched_json TEXT NOT NULL, embed_text TEXT,
                missing_info TEXT NOT NULL DEFAULT '[]', low_quality INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL);
        """)
        g = make_game(id_product=5)
        legacy.execute(
            "INSERT INTO products (id_product, name, original_json, enriched_json, updated_at)"
            " VALUES (?,?,?,?,?)",
            (5, g.original.name, g.original.model_dump_json(), g.enriched.model_dump_json(), "t0"),
        )
        legacy.commit()
        legacy.close()

        s = EnrichmentStore(path=db)  # opening triggers _migrate()
        assert s.get_game(5).extracted == {}          # legacy row survives, default applied
        s.save_game(make_game(id_product=6).model_copy(update={"extracted": {"genere": "gestionale"}}))
        assert s.get_game(6).extracted == {"genere": "gestionale"}
        s.close()

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
