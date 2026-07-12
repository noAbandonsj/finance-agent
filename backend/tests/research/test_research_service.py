from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

import pytest
from langchain_core.tools import BaseTool

from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.records.database import Database
from ai_finance.records.models import Base
from ai_finance.records.repositories import AnalysisRepository
from ai_finance.research.service import ResearchService


class FixedMarketService:
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


class FixedRunner:
    def __init__(self, tools: Sequence[BaseTool], *, use_tools: bool) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._use_tools = use_tools

    async def run(self, user_query: str, thread_id: str) -> str:
        assert "Security symbol: 600519.SH" in user_query
        if self._use_tools:
            await self._tools["get_market_snapshot"].ainvoke({"symbol": "600519"})
            await self._tools["calculate_market_metrics"].ainvoke(
                {"symbol": "600519", "trading_days": 10}
            )
        return "# 研究报告\n\n结论保持中性。"


class FailingRunner:
    async def run(self, user_query: str, thread_id: str) -> str:
        raise RuntimeError("synthetic model failure")


def runner_factory(*, fail: bool = False, use_tools: bool = True):
    @asynccontextmanager
    async def factory(tools: Sequence[BaseTool]) -> AsyncIterator[object]:
        if fail:
            yield FailingRunner()
        else:
            yield FixedRunner(tools, use_tools=use_tools)

    return factory


def make_service(tmp_path, *, fail: bool = False, use_tools: bool = True):
    database = Database(f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(database.engine)
    repository = AnalysisRepository(database)
    service = ResearchService(
        analysis_repository=repository,
        market_service=FixedMarketService(),
        metrics_service=MarketMetricsService(),
        runner_factory=runner_factory(fail=fail, use_tools=use_tools),
        model_name="test-model",
        prompt_version="research-v2",
    )
    return service, repository


@pytest.mark.asyncio
async def test_run_records_tool_progress_report_and_completion(tmp_path) -> None:
    service, repository = make_service(tmp_path)
    run = await service.start("analyze", "600519")

    await service.execute(run.id)

    detail = repository.get_run(run.id)
    assert detail.status == "COMPLETE"
    assert [event.event_type for event in detail.events] == [
        "RUN_CREATED",
        "AGENT_STARTED",
        "TOOL_STARTED",
        "TOOL_COMPLETED",
        "TOOL_STARTED",
        "TOOL_COMPLETED",
        "AGENT_COMPLETED",
        "RUN_COMPLETED",
    ]
    assert detail.events[-1].terminal is True
    assert detail.result is not None
    assert detail.result.report_markdown.startswith("# 研究报告")
    assert detail.data_cutoff == datetime(2026, 7, 11, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_run_can_complete_without_tools_or_data_cutoff(tmp_path) -> None:
    service, repository = make_service(tmp_path, use_tools=False)
    run = await service.start("explain the methodology", "600519")

    await service.execute(run.id)

    detail = repository.get_run(run.id)
    assert detail.status == "COMPLETE"
    assert detail.data_cutoff is None
    assert detail.tool_calls == []
    assert detail.result is not None


@pytest.mark.asyncio
async def test_runner_failure_is_persisted_as_terminal_event(tmp_path) -> None:
    service, repository = make_service(tmp_path, fail=True)
    run = await service.start("analyze", "600519")

    await service.execute(run.id)

    detail = repository.get_run(run.id)
    assert detail.status == "FAILED"
    assert detail.error_code == "RUNTIMEERROR"
    assert detail.error_message == "synthetic model failure"
    assert detail.events[-1].event_type == "RUN_FAILED"
    assert detail.events[-1].terminal is True
