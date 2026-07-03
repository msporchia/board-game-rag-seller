"""ExchangeDir — layout creation and sequence-id resumption.

`next_seq()` must be globally monotonic across every kind sharing one exchange directory, and
must RESUME above whatever is already on disk (pending/replies/answered/rejected) rather than
restart at 1 — a runner restarted against a non-empty directory must never reissue a sequence id
a responder already answered or rejected.
"""

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir


class TestSequence:
    def test_creates_the_four_subdirectories(self, tmp_path):
        exchange = ExchangeDir(tmp_path / "exchange")

        assert exchange.pending.is_dir()
        assert exchange.replies.is_dir()
        assert exchange.rejected.is_dir()
        assert exchange.answered.is_dir()

    def test_fresh_directory_starts_at_one(self, tmp_path):
        exchange = ExchangeDir(tmp_path)

        assert exchange.next_seq() == 1
        assert exchange.next_seq() == 2

    def test_resumes_above_the_highest_existing_sequence_id(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        (exchange.pending / "00003-pitch.json").write_text("{}", encoding="utf-8")
        (exchange.answered / "00007-analysis.json").write_text("{}", encoding="utf-8")
        (exchange.rejected / "00005-2.json").write_text("{}", encoding="utf-8")

        resumed = ExchangeDir(tmp_path)

        assert resumed.next_seq() == 8
