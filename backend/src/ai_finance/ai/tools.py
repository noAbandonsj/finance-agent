import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime, time, timezone
from time import perf_counter
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.service import MarketDataService
from ai_finance.records.models import NewToolCallRecord
from ai_finance.records.repositories import AnalysisRepository


class DuplicateToolCallError(RuntimeError):
    code = "DUPLICATE_TOOL_CALL"


MARKET_OPERATION_TIMEOUT_SECONDS = 20.0


class ResearchToolFactory:
    def __init__(
        self,
        run_id: str,
        market_service: MarketDataService,
        metrics_service: MarketMetricsService,
        analysis_repository: AnalysisRepository,
    ) -> None:
        self._run_id = run_id
        self._market_service = market_service
        self._metrics_service = metrics_service
        self._repository = analysis_repository
        self._seen_calls: set[str] = set()
        self._seen_lock = asyncio.Lock()

    def create_tools(self) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                coroutine=self.get_security_profile,
                name="get_security_profile",
                description="Get canonical security identity and type for an A-share or ETF.",
            ),
            StructuredTool.from_function(
                coroutine=self.get_market_snapshot,
                name="get_market_snapshot",
                description="Get the latest available normalized market snapshot.",
            ),
            StructuredTool.from_function(
                coroutine=self.get_price_history,
                name="get_price_history",
                description="Get normalized ascending daily price history.",
            ),
            StructuredTool.from_function(
                coroutine=self.calculate_market_metrics,
                name="calculate_market_metrics",
                description="Calculate deterministic returns, trend, volatility, and drawdown.",
            ),
        ]

    async def get_security_profile(self, symbol: str) -> dict[str, object]:
        async def operation() -> tuple[dict[str, object], str | None, datetime | None, datetime]:
            profile = await asyncio.wait_for(
                asyncio.to_thread(self._market_service.get_security_profile, symbol),
                timeout=MARKET_OPERATION_TIMEOUT_SECONDS,
            )
            return (
                profile.model_dump(mode="json"),
                profile.provider,
                None,
                profile.retrieved_at,
            )

        return await self._execute("get_security_profile", {"symbol": symbol}, operation)

    async def get_market_snapshot(self, symbol: str) -> dict[str, object]:
        async def operation() -> tuple[dict[str, object], str | None, datetime | None, datetime]:
            snapshot = await asyncio.wait_for(
                asyncio.to_thread(self._market_service.get_market_snapshot, symbol),
                timeout=MARKET_OPERATION_TIMEOUT_SECONDS,
            )
            return (
                snapshot.model_dump(mode="json"),
                snapshot.provider,
                snapshot.market_time,
                snapshot.retrieved_at,
            )

        return await self._execute("get_market_snapshot", {"symbol": symbol}, operation)

    async def get_price_history(self, symbol: str, trading_days: int = 120) -> dict[str, object]:
        arguments = {"symbol": symbol, "trading_days": trading_days}

        async def operation() -> tuple[dict[str, object], str | None, datetime | None, datetime]:
            bars = await asyncio.wait_for(
                asyncio.to_thread(self._market_service.get_daily_bars, symbol, trading_days),
                timeout=MARKET_OPERATION_TIMEOUT_SECONDS,
            )
            retrieved_at = datetime.now(timezone.utc)
            market_time = (
                datetime.combine(bars[-1].trading_date, time.min, tzinfo=timezone.utc)
                if bars
                else None
            )
            return (
                {
                    "symbol": bars[0].symbol if bars else symbol,
                    "bars": [bar.model_dump(mode="json") for bar in bars],
                },
                bars[0].provider if bars else None,
                market_time,
                retrieved_at,
            )

        return await self._execute("get_price_history", arguments, operation)

    async def calculate_market_metrics(
        self, symbol: str, trading_days: int = 120
    ) -> dict[str, object]:
        arguments = {"symbol": symbol, "trading_days": trading_days}

        async def operation() -> tuple[dict[str, object], str | None, datetime | None, datetime]:
            bars = await asyncio.wait_for(
                asyncio.to_thread(self._market_service.get_daily_bars, symbol, trading_days),
                timeout=MARKET_OPERATION_TIMEOUT_SECONDS,
            )
            canonical_symbol = bars[0].symbol if bars else symbol
            metrics = await asyncio.to_thread(
                self._metrics_service.calculate, canonical_symbol, bars
            )
            retrieved_at = datetime.now(timezone.utc)
            market_time = datetime.combine(metrics.end_date, time.min, tzinfo=timezone.utc)
            return metrics.model_dump(mode="json"), bars[0].provider, market_time, retrieved_at

        return await self._execute("calculate_market_metrics", arguments, operation)

    async def _execute(
        self,
        tool_name: str,
        arguments: dict[str, object],
        operation: Callable[
            [], Awaitable[tuple[dict[str, object], str | None, datetime | None, datetime]]
        ],
    ) -> dict[str, object]:
        call_key = json.dumps(
            {"tool": tool_name, "arguments": arguments},
            sort_keys=True,
            separators=(",", ":"),
        )
        async with self._seen_lock:
            if call_key in self._seen_calls:
                raise DuplicateToolCallError(f"Duplicate tool call: {tool_name}")
            self._seen_calls.add(call_key)

        started = perf_counter()
        try:
            result, provider, market_time, retrieved_at = await operation()
        except Exception as exc:
            await self._record(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                provider=None,
                market_time=None,
                retrieved_at=datetime.now(timezone.utc),
                duration_ms=_duration_ms(started),
                success=False,
                error_code=getattr(exc, "code", type(exc).__name__.upper()),
            )
            raise

        record = await self._record(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            provider=provider,
            market_time=market_time,
            retrieved_at=retrieved_at,
            duration_ms=_duration_ms(started),
            success=True,
            error_code=None,
        )
        return {**result, "evidence_id": record.id}

    async def _record(self, **values: Any):
        record = NewToolCallRecord(run_id=self._run_id, **values)
        return await asyncio.to_thread(self._repository.record_tool_call, record)


def _duration_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
