"""SQLiteTraceHandler unit tests: offline and deterministic.

End-to-end through LangChain's real callback plumbing (`FakeListLLM`) plus direct
invocations of the handler hooks for the cases the fake LLM cannot produce (Ollama token
metadata, errors). The store goes to a temp SQLite — no shared state, no Ollama.
"""

from uuid import uuid4

import pytest
from langchain_core.language_models import FakeListLLM
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation, LLMResult

from app.core.tracing.handler import SQLiteTraceHandler
from app.core.tracing.store import TraceStore


@pytest.fixture
def store(tmp_path):
    s = TraceStore(path=str(tmp_path / "traces.db"))
    yield s
    s.close()


def test_records_fake_llm_run_end_to_end(store):
    """A real LangChain run (FakeListLLM) lands in the traces table with prompt/response
    sizes, component attribution and a measured duration."""
    handler = SQLiteTraceHandler(component="curator", store=store)
    llm = FakeListLLM(responses=["una risposta"], callbacks=[handler])

    llm.invoke("che gioco per due giocatori?")

    rows = store.get_traces()
    assert len(rows) == 1
    row = rows[0]
    assert row["component"] == "curator"
    assert row["prompt_chars"] == len("che gioco per due giocatori?")
    assert "che gioco" in row["prompt_preview"]
    assert row["response_chars"] == len("una risposta")
    assert row["duration_ms"] >= 0
    assert row["error"] is None
    assert row["run_id"]
    assert row["created_at"]


def test_token_counts_from_usage_metadata(store):
    """langchain-ollama puts {input,output,total}_tokens on AIMessage.usage_metadata —
    the handler records input/output tokens and the model from invocation_params."""
    handler = SQLiteTraceHandler(component="synth", store=store)
    run_id = uuid4()
    handler.on_llm_start({}, ["materiale..."], run_id=run_id,
                         invocation_params={"model": "llama3.1"})
    msg = AIMessage(content="sintesi",
                    usage_metadata={"input_tokens": 32, "output_tokens": 71,
                                    "total_tokens": 103})
    handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=msg)]]), run_id=run_id)

    row = store.get_traces("synth")[0]
    assert row["model"] == "llama3.1"
    assert (row["input_tokens"], row["output_tokens"]) == (32, 71)


def test_token_counts_fallback_generation_info(store):
    """Without usage_metadata, Ollama's raw counters in generation_info
    (prompt_eval_count / eval_count) are used."""
    handler = SQLiteTraceHandler(component="web", store=store)
    run_id = uuid4()
    handler.on_llm_start({}, ["pagina..."], run_id=run_id, invocation_params={})
    gen = Generation(text="estratto",
                     generation_info={"prompt_eval_count": 10, "eval_count": 4})
    handler.on_llm_end(LLMResult(generations=[[gen]]), run_id=run_id)

    row = store.get_traces("web")[0]
    assert (row["input_tokens"], row["output_tokens"]) == (10, 4)


def test_error_recorded(store):
    handler = SQLiteTraceHandler(component="curator", store=store)
    run_id = uuid4()
    handler.on_llm_start({}, ["prompt"], run_id=run_id, invocation_params={})
    handler.on_llm_error(RuntimeError("ollama down"), run_id=run_id)

    row = store.get_traces()[0]
    assert "ollama down" in row["error"]
    assert row["response_chars"] is None
    assert row["duration_ms"] >= 0


def test_long_prompt_is_truncated_in_preview(store):
    handler = SQLiteTraceHandler(component="curator", store=store)
    run_id = uuid4()
    prompt = "x" * 5000
    handler.on_llm_start({}, [prompt], run_id=run_id, invocation_params={})
    handler.on_llm_end(LLMResult(generations=[[Generation(text="ok")]]), run_id=run_id)

    row = store.get_traces()[0]
    assert row["prompt_chars"] == 5000
    assert len(row["prompt_preview"]) == SQLiteTraceHandler.PREVIEW_CHARS


def test_end_without_start_is_a_noop(store):
    """An unmatched on_llm_end must not raise nor write a row."""
    handler = SQLiteTraceHandler(component="curator", store=store)
    handler.on_llm_end(LLMResult(generations=[[Generation(text="ok")]]), run_id=uuid4())
    assert store.get_traces() == []


def test_store_failure_never_breaks_the_call_path(caplog):
    """A broken store (e.g. disk full) logs a warning; the hooks never raise."""

    class BrokenStore:
        def save_trace(self, **kwargs):
            raise RuntimeError("disk full")

    handler = SQLiteTraceHandler(component="curator", store=BrokenStore())
    run_id = uuid4()
    with caplog.at_level("WARNING", logger="app.core.tracing"):
        handler.on_llm_start({}, ["prompt"], run_id=run_id, invocation_params={})
        handler.on_llm_end(LLMResult(generations=[[Generation(text="ok")]]), run_id=run_id)
    # structlog routes into stdlib: the record's msg is the event dict, event name included
    assert any("trace_write_failed" in r.getMessage() for r in caplog.records)
