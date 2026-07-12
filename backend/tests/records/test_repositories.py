from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier, Lock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import event

from ai_finance.records.database import Database
from ai_finance.records.models import CompletedAnalysisRecord, NewToolCallRecord
from ai_finance.records.repositories import AnalysisRepository, WatchlistRepository


BACKEND_ROOT = Path(__file__).parents[2]


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database_url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    database = Database(database_url)
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture
def analysis_repository(database: Database) -> AnalysisRepository:
    return AnalysisRepository(database)


def create_run(repository: AnalysisRepository):
    return repository.create_run(
        user_query="Analyze this security",
        symbol="600519",
        model_name="deepseek-v4-pro",
        prompt_version="research-v1",
        thread_id="thread-1",
    )


def make_completed_result() -> CompletedAnalysisRecord:
    return CompletedAnalysisRecord(report_markdown="# Research report\n\nMomentum is positive.")


def make_tool_call(
    run_id: str, market_time: datetime | None, retrieved_at: datetime
) -> NewToolCallRecord:
    return NewToolCallRecord(
        run_id=run_id,
        tool_name="get_market_snapshot",
        arguments={"symbol": "600519.SH"},
        result={"last": 1500.0},
        provider="akshare",
        market_time=market_time,
        retrieved_at=retrieved_at,
        duration_ms=25,
        success=True,
    )


def test_created_run_starts_running_with_canonical_symbol(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)

    UUID(run.id)
    assert run.status == "RUNNING"
    assert run.symbol == "600519.SH"
    assert run.finished_at is None
    assert run.started_at.tzinfo is not None
    assert analysis_repository.get_run(run.id).id == run.id


def test_event_sequences_start_at_one_and_listing_returns_later_events_in_order(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)

    first = analysis_repository.append_event(
        run.id, "RUN_STARTED", "Started", {"step": 1}, terminal=False
    )
    second = analysis_repository.append_event(
        run.id, "TOOL_STARTED", "Loading market data", None, terminal=False
    )
    third = analysis_repository.append_event(
        run.id, "RUN_COMPLETE", "Complete", {"step": 3}, terminal=True
    )

    assert [first.sequence, second.sequence, third.sequence] == [1, 2, 3]
    later_events = analysis_repository.list_events(run.id, after_sequence=1)
    assert [event.sequence for event in later_events] == [2, 3]
    assert [event.message for event in later_events] == ["Loading market data", "Complete"]
    assert later_events[-1].payload == {"step": 3}
    assert later_events[-1].terminal is True


def test_concurrent_event_appends_persist_distinct_sequences(
    analysis_repository: AnalysisRepository, database: Database
) -> None:
    run = create_run(analysis_repository)
    sequence_read_barrier = Barrier(2)
    query_count_lock = Lock()
    sequence_query_count = 0

    def synchronize_initial_sequence_reads(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        nonlocal sequence_query_count
        if "max(analysis_event.sequence)" not in statement:
            return
        with query_count_lock:
            sequence_query_count += 1
            should_wait = sequence_query_count <= 2
        if should_wait:
            sequence_read_barrier.wait(timeout=5)

    event.listen(database.engine, "after_cursor_execute", synchronize_initial_sequence_reads)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    analysis_repository.append_event,
                    run.id,
                    "PROGRESS",
                    message,
                    None,
                    False,
                )
                for message in ("First concurrent event", "Second concurrent event")
            ]
            appended_events = [future.result(timeout=10) for future in futures]
    finally:
        event.remove(database.engine, "after_cursor_execute", synchronize_initial_sequence_reads)

    assert sorted(event.sequence for event in appended_events) == [1, 2]
    persisted_events = analysis_repository.list_events(run.id, after_sequence=0)
    assert [event.sequence for event in persisted_events] == [1, 2]
    assert {event.message for event in persisted_events} == {
        "First concurrent event",
        "Second concurrent event",
    }


def test_tool_record_returns_generated_evidence_id_and_can_be_listed(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)
    market_time = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)
    retrieved_at = datetime(2026, 7, 10, 7, 0, 1, tzinfo=timezone.utc)

    tool_record = analysis_repository.record_tool_call(
        NewToolCallRecord(
            run_id=run.id,
            tool_name="get_market_snapshot",
            arguments={"symbol": "600519.SH"},
            result={"last": 1500.0},
            provider="akshare",
            market_time=market_time,
            retrieved_at=retrieved_at,
            duration_ms=25,
            success=True,
        )
    )

    UUID(tool_record.id)
    assert tool_record.arguments == {"symbol": "600519.SH"}
    assert tool_record.result == {"last": 1500.0}
    assert tool_record.market_time == market_time
    listed_tool_calls = analysis_repository.list_tool_calls(run.id)
    assert listed_tool_calls == [tool_record]
    assert listed_tool_calls[0].arguments == {"symbol": "600519.SH"}
    assert listed_tool_calls[0].result == {"last": 1500.0}


def test_completed_analysis_requires_non_empty_report() -> None:
    with pytest.raises(ValidationError, match="at least 1 character"):
        CompletedAnalysisRecord(report_markdown="")


def test_new_tool_call_requires_aware_market_time() -> None:
    retrieved_at = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="timezone_aware"):
        make_tool_call("run-1", datetime(2026, 7, 10, 15, 0), retrieved_at)


def test_new_tool_call_requires_aware_retrieved_at() -> None:
    market_time = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="timezone_aware"):
        make_tool_call("run-1", market_time, datetime(2026, 7, 10, 15, 0))


def test_nullable_market_time_remains_valid() -> None:
    retrieved_at = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)

    assert make_tool_call("run-1", None, retrieved_at).market_time is None


def test_asia_shanghai_inputs_round_trip_as_same_utc_instants(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)
    shanghai = ZoneInfo("Asia/Shanghai")
    market_time = datetime(2026, 7, 10, 15, 0, tzinfo=shanghai)
    retrieved_at = datetime(2026, 7, 10, 15, 0, 1, tzinfo=shanghai)

    saved_tool_call = analysis_repository.record_tool_call(
        make_tool_call(run.id, market_time, retrieved_at)
    )
    completed_run = analysis_repository.complete_run(run.id, make_completed_result())
    reloaded_tool_call = analysis_repository.list_tool_calls(run.id)[0]
    detail = analysis_repository.get_run(run.id)

    assert saved_tool_call.market_time == market_time.astimezone(timezone.utc)
    assert saved_tool_call.retrieved_at == retrieved_at.astimezone(timezone.utc)
    assert reloaded_tool_call.market_time == market_time.astimezone(timezone.utc)
    assert reloaded_tool_call.retrieved_at == retrieved_at.astimezone(timezone.utc)
    assert completed_run.data_cutoff == market_time.astimezone(timezone.utc)
    assert detail.data_cutoff == market_time.astimezone(timezone.utc)
    assert reloaded_tool_call.market_time is not None
    assert reloaded_tool_call.market_time.tzinfo is timezone.utc
    assert reloaded_tool_call.retrieved_at.tzinfo is timezone.utc
    assert completed_run.data_cutoff is not None
    assert completed_run.data_cutoff.tzinfo is timezone.utc
    assert detail.data_cutoff is not None
    assert detail.data_cutoff.tzinfo is timezone.utc


def test_completing_run_persists_result_and_complete_status_atomically(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)
    data_cutoff = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)
    analysis_repository.record_tool_call(
        make_tool_call(run.id, data_cutoff, data_cutoff)
    )
    completed_result = make_completed_result()

    completed_run = analysis_repository.complete_run(run.id, completed_result)
    detail = analysis_repository.get_run(run.id)

    assert completed_run.status == "COMPLETE"
    assert completed_run.finished_at is not None
    assert completed_run.finished_at.tzinfo is not None
    assert completed_run.data_cutoff == data_cutoff
    assert detail.status == "COMPLETE"
    assert detail.result is not None
    assert detail.result.report_markdown == completed_result.report_markdown


def test_completing_run_without_tools_keeps_data_cutoff_null(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)
    analysis_repository.complete_run(run.id, make_completed_result())

    detail = analysis_repository.get_run(run.id)
    assert detail.status == "COMPLETE"
    assert detail.finished_at is not None
    assert detail.data_cutoff is None
    assert detail.result is not None


def test_failing_run_records_typed_error_and_history_is_paginated(
    analysis_repository: AnalysisRepository,
) -> None:
    first_run = create_run(analysis_repository)
    second_run = analysis_repository.create_run(
        user_query="Analyze an ETF",
        symbol="510300",
        model_name="deepseek-v4-flash",
        prompt_version="research-v1",
        thread_id="thread-2",
    )

    failed_run = analysis_repository.fail_run(
        second_run.id, "MODEL_UNAVAILABLE", "The model request failed"
    )

    assert failed_run.status == "FAILED"
    assert failed_run.error_code == "MODEL_UNAVAILABLE"
    assert failed_run.error_message == "The model request failed"
    assert failed_run.finished_at is not None
    assert analysis_repository.get_run(second_run.id).status == "FAILED"
    listed_ids = {
        item.id
        for offset in (0, 1)
        for item in analysis_repository.list_runs(limit=1, offset=offset)
    }
    assert listed_ids == {first_run.id, second_run.id}


def test_watchlist_insertion_is_idempotent_by_canonical_symbol(database: Database) -> None:
    repository = WatchlistRepository(database)

    first = repository.add(
        symbol="600519", display_name="Kweichow Moutai", security_type="STOCK", note="Core"
    )
    second = repository.add(
        symbol="SH600519",
        display_name="Duplicate name",
        security_type="STOCK",
        note="Duplicate note",
    )

    assert first.symbol == "600519.SH"
    assert second == first
    assert repository.get("600519.sh") == first
    assert repository.list_items() == [first]

    assert repository.remove("600519") is True
    assert repository.remove("600519") is False
    assert repository.list_items() == []
