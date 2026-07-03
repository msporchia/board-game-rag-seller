"""SimUsageTracker — the `llm_usage.snapshot()/delta_since()` interface `ConversationDriver`
expects, aggregating `.calls` across every tracked FileExchange* stand-in instead of counting
real Ollama token usage (there is none to count in a simulated run)."""

from tests.eval.ChatConversation.simulation.sim_usage_tracker import SimUsageTracker


class _Countable:
    def __init__(self):
        self.calls = 0


class TestUsageTracker:
    def test_snapshot_sums_calls_across_tracked_llms_with_zero_tokens(self):
        tracker = SimUsageTracker()
        pitch, intent = _Countable(), _Countable()
        tracker.track(pitch)
        tracker.track(intent)
        pitch.calls = 2
        intent.calls = 3

        snapshot = tracker.snapshot()

        assert snapshot == {"llm_calls": 5, "tokens_in": 0, "tokens_out": 0}

    def test_delta_since_reports_only_the_calls_made_after_the_snapshot(self):
        tracker = SimUsageTracker()
        pitch = _Countable()
        tracker.track(pitch)
        before = tracker.snapshot()
        pitch.calls += 4

        delta = tracker.delta_since(before)

        assert delta == {"llm_calls": 4, "tokens_in": 0, "tokens_out": 0}
