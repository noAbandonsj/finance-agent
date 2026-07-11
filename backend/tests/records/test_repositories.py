from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config

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
    assert tool_record.result == {"last": 1500.0}
    assert tool_record.market_time == market_time
    assert analysis_repository.list_tool_calls(run.id) == [tool_record]


def test_completing_run_persists_result_and_complete_status_atomically(
    analysis_repository: AnalysisRepository,
) -> None:
    run = create_run(analysis_repository)
    data_cutoff = datetime(2026, 7, 10, 7, 0, tzinfo=timezone.utc)
    completed_result = CompletedAnalysisRecord(
        market_view="BULLISH",
        horizon="20 trading days",
        confidence=0.74,
        summary="Momentum is positive.",
        supporting_evidence=[{"evidence_id": "evidence-1", "statement": "Positive return"}],
        opposing_evidence=[{"evidence_id": "evidence-2", "statement": "Elevated volatility"}],
        risks=["Policy change"],
        invalidation_conditions=["Close below the 20-day average"],
        full_result={"status": "COMPLETE", "symbol": "600519.SH"},
        data_cutoff=data_cutoff,
    )

    completed_run = analysis_repository.complete_run(run.id, completed_result)
    detail = analysis_repository.get_run(run.id)

    assert completed_run.status == "COMPLETE"
    assert completed_run.finished_at is not None
    assert completed_run.finished_at.tzinfo is not None
    assert completed_run.data_cutoff == data_cutoff
    assert detail.status == "COMPLETE"
    assert detail.result is not None
    assert detail.result.market_view == "BULLISH"
    assert detail.result.supporting_evidence == completed_result.supporting_evidence
    assert detail.result.full_result == completed_result.full_result


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
