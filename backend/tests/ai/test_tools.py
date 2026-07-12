from datetime import date, datetime, timezone

import pytest

from ai_finance.ai.tools import DuplicateToolCallError, ResearchToolFactory
from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.records.database import Database
from ai_finance.records.models import Base
from ai_finance.records.repositories import AnalysisRepository


class FixedMarketService:
    def __init__(self) -> None:
        self.snapshot_calls = 0

    def get_security_profile(self, symbol: str) -> SecurityProfile:
        return SecurityProfile(
            symbol="600519.SH",
            name="Kweichow Moutai",
            security_type=SecurityType.STOCK,
            exchange="SH",
            provider="test",
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        self.snapshot_calls += 1
        return MarketSnapshot(
            symbol="600519.SH",
            name="Kweichow Moutai",
            security_type=SecurityType.STOCK,
            last=1400,
            previous_close=1390,
            open=1395,
            high=1410,
            low=1388,
            change_percent=0.72,
            volume=100,
            amount=140000,
            market_time=datetime(2026, 7, 11, tzinfo=timezone.utc),
            timestamp_origin="retrieval_time",
            provider="test",
            retrieved_at=datetime(2026, 7, 11, 0, 0, 1, tzinfo=timezone.utc),
        )

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        return [
            DailyBar(
                symbol="600519.SH",
                trading_date=date(2026, 7, day),
                open=float(day),
                high=float(day),
                low=float(day),
                close=float(day),
                volume=100,
                amount=1000,
                provider="test",
            )
            for day in range(1, min(trading_days, 10) + 1)
        ]


def make_tools(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(database.engine)
    repository = AnalysisRepository(database)
    run = repository.create_run(
        user_query="analyze",
        symbol="600519",
        model_name="test-model",
        prompt_version="research-v1",
        thread_id="thread-1",
    )
    market_service = FixedMarketService()
    tools = ResearchToolFactory(
        run_id=run.id,
        market_service=market_service,
        metrics_service=MarketMetricsService(),
        analysis_repository=repository,
    ).create_tools()
    return {tool.name: tool for tool in tools}, repository, run.id, market_service


@pytest.mark.asyncio
async def test_tool_persists_result_and_returns_evidence_id(tmp_path) -> None:
    tools, repository, run_id, _market_service = make_tools(tmp_path)

    result = await tools["get_market_snapshot"].ainvoke({"symbol": "600519"})
    records = repository.list_tool_calls(run_id)

    assert len(records) == 1
    assert result["evidence_id"] == records[0].id
    assert result["symbol"] == "600519.SH"
    assert records[0].success is True
    assert records[0].market_time == datetime(2026, 7, 11, tzinfo=timezone.utc)
    events = repository.list_events(run_id, 0)
    assert [event.event_type for event in events] == ["TOOL_STARTED", "TOOL_COMPLETED"]
    assert events[-1].payload == {
        "tool_name": "get_market_snapshot",
        "duration_ms": records[0].duration_ms,
        "evidence_id": records[0].id,
    }


@pytest.mark.asyncio
async def test_identical_tool_call_cannot_execute_twice(tmp_path) -> None:
    tools, repository, run_id, market_service = make_tools(tmp_path)
    tool = tools["get_market_snapshot"]

    await tool.ainvoke({"symbol": "600519"})
    duplicate_result = await tool.ainvoke({"symbol": "600519"})

    assert f"[{DuplicateToolCallError.code}]" in duplicate_result
    assert market_service.snapshot_calls == 1
    assert len(repository.list_tool_calls(run_id)) == 1
    assert repository.list_events(run_id, 0)[-1].event_type == "TOOL_FAILED"


@pytest.mark.asyncio
async def test_metrics_tool_uses_deterministic_calculator(tmp_path) -> None:
    tools, _repository, _run_id, _market_service = make_tools(tmp_path)

    result = await tools["calculate_market_metrics"].ainvoke(
        {"symbol": "600519", "trading_days": 10}
    )

    assert result["observation_count"] == 10
    assert result["returns"]["5d"] == pytest.approx(1.0)
    assert result["evidence_id"]


@pytest.mark.asyncio
async def test_tool_failure_is_recorded_and_returned_to_the_agent(tmp_path, monkeypatch) -> None:
    tools, repository, run_id, market_service = make_tools(tmp_path)

    def fail_snapshot(symbol: str) -> MarketSnapshot:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(market_service, "get_market_snapshot", fail_snapshot)
    result = await tools["get_market_snapshot"].ainvoke({"symbol": "600519"})

    assert "Tool error [RUNTIMEERROR]" in result
    records = repository.list_tool_calls(run_id)
    assert len(records) == 1
    assert records[0].success is False
    assert records[0].error_code == "RUNTIMEERROR"
    assert [event.event_type for event in repository.list_events(run_id, 0)] == [
        "TOOL_STARTED",
        "TOOL_FAILED",
    ]
