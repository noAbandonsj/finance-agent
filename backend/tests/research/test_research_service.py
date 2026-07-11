from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

import pytest
from langchain_core.tools import BaseTool

from ai_finance.ai.schemas import AnalysisStatus, EvidenceItem, MarketView, ResearchAnalysis
from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.records.database import Database
from ai_finance.records.models import Base, NewToolCallRecord
from ai_finance.records.repositories import AnalysisRepository
from ai_finance.research.service import ResearchService
from ai_finance.research.validator import EvidenceValidationError, EvidenceValidator


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


class ToolCallingRunner:
    def __init__(self, tools: Sequence[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    async def run(self, user_query: str, thread_id: str) -> ResearchAnalysis:
        snapshot = await self._tools["get_market_snapshot"].ainvoke({"symbol": "600519"})
        metrics = await self._tools["calculate_market_metrics"].ainvoke(
            {"symbol": "600519", "trading_days": 10}
        )
        return make_analysis(snapshot["evidence_id"], metrics["evidence_id"])


class FailingRunner:
    async def run(self, user_query: str, thread_id: str) -> ResearchAnalysis:
        raise RuntimeError("synthetic model failure")


def runner_factory(fail: bool = False):
    @asynccontextmanager
    async def factory(tools: Sequence[BaseTool]) -> AsyncIterator[object]:
        yield FailingRunner() if fail else ToolCallingRunner(tools)

    return factory


def make_analysis(snapshot_id: str, metrics_id: str) -> ResearchAnalysis:
    now = datetime(2026, 7, 11, tzinfo=timezone.utc)
    return ResearchAnalysis(
        status=AnalysisStatus.COMPLETE,
        symbol="600519.SH",
        security_name="Kweichow Moutai",
        market_view=MarketView.NEUTRAL,
        horizon="20 trading days",
        confidence=0.6,
        summary="Balanced.",
        supporting_evidence=[EvidenceItem(evidence_id=snapshot_id, statement="price")],
        opposing_evidence=[EvidenceItem(evidence_id=metrics_id, statement="risk")],
        risks=["volatility"],
        invalidation_conditions=["trend changes"],
        data_cutoff=now,
        generated_at=now,
        model_name="test-model",
        prompt_version="research-v1",
    )


def make_service(tmp_path, *, fail: bool = False):
    database = Database(f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(database.engine)
    repository = AnalysisRepository(database)
    service = ResearchService(
        analysis_repository=repository,
        market_service=FixedMarketService(),
        metrics_service=MarketMetricsService(),
        runner_factory=runner_factory(fail),
        model_name="test-model",
        prompt_version="research-v1",
    )
    return service, repository


@pytest.mark.asyncio
async def test_run_records_ordered_progress_and_completion(tmp_path) -> None:
    service, repository = make_service(tmp_path)
    run = await service.start("analyze", "600519")

    await service.execute(run.id)

    detail = repository.get_run(run.id)
    assert detail.status == "COMPLETE"
    assert [event.event_type for event in detail.events] == [
        "RUN_CREATED",
        "AGENT_STARTED",
        "AGENT_COMPLETED",
        "RUN_COMPLETED",
    ]
    assert detail.events[-1].terminal is True
    assert detail.result is not None
    assert detail.result.market_view == "NEUTRAL"


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


def test_validator_rejects_evidence_from_another_run(tmp_path) -> None:
    _service, repository = make_service(tmp_path)
    first = repository.create_run("one", "600519", "m", "p", "t1")
    second = repository.create_run("two", "600519", "m", "p", "t2")
    foreign = repository.record_tool_call(
        NewToolCallRecord(
            run_id=first.id,
            tool_name="get_market_snapshot",
            arguments={},
            result={},
            provider="test",
            market_time=datetime(2026, 7, 11, tzinfo=timezone.utc),
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
            duration_ms=1,
            success=True,
        )
    )
    analysis = make_analysis(foreign.id, foreign.id)

    with pytest.raises(EvidenceValidationError):
        EvidenceValidator(repository).validate(second.id, analysis)


def test_missing_required_market_tools_becomes_insufficient_data(tmp_path) -> None:
    _service, repository = make_service(tmp_path)
    run = repository.create_run("one", "600519", "m", "p", "t1")
    profile = repository.record_tool_call(
        NewToolCallRecord(
            run_id=run.id,
            tool_name="get_security_profile",
            arguments={},
            result={},
            provider="test",
            market_time=None,
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
            duration_ms=1,
            success=True,
        )
    )

    validated = EvidenceValidator(repository).validate(
        run.id, make_analysis(profile.id, profile.id)
    )

    assert validated.status is AnalysisStatus.INSUFFICIENT_DATA
    assert validated.market_view is MarketView.UNCERTAIN
