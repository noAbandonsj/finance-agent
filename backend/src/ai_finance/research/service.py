import asyncio
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import uuid4

from langchain_core.tools import BaseTool

from ai_finance.ai.prompt import PROMPT_VERSION
from ai_finance.ai.schemas import ResearchAnalysis
from ai_finance.ai.tools import ResearchToolFactory
from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.service import MarketDataService
from ai_finance.records.models import AnalysisRunRecord
from ai_finance.records.repositories import AnalysisRepository
from ai_finance.research.validator import AnalysisRecordMapper, EvidenceValidator


class ResearchRunner(Protocol):
    async def run(self, user_query: str, thread_id: str) -> ResearchAnalysis: ...


RunnerFactory = Callable[[Sequence[BaseTool]], AbstractAsyncContextManager[ResearchRunner]]


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, coroutine) -> asyncio.Task[None]:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    @property
    def active_count(self) -> int:
        return len(self._tasks)


class ResearchService:
    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        market_service: MarketDataService,
        metrics_service: MarketMetricsService,
        runner_factory: RunnerFactory,
        model_name: str,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self._repository = analysis_repository
        self._market_service = market_service
        self._metrics_service = metrics_service
        self._runner_factory = runner_factory
        self._model_name = model_name
        self._prompt_version = prompt_version
        self._validator = EvidenceValidator(analysis_repository)

    async def start(self, user_query: str, symbol: str) -> AnalysisRunRecord:
        thread_id = str(uuid4())
        run = await asyncio.to_thread(
            self._repository.create_run,
            user_query,
            symbol,
            self._model_name,
            self._prompt_version,
            thread_id,
        )
        await asyncio.to_thread(
            self._repository.append_event,
            run.id,
            "RUN_CREATED",
            "Research run created",
            {},
            False,
        )
        return run

    async def execute(self, run_id: str) -> None:
        run = await asyncio.to_thread(self._repository.get_run, run_id)
        await asyncio.to_thread(
            self._repository.append_event,
            run_id,
            "AGENT_STARTED",
            "AI research started",
            {},
            False,
        )
        tools = ResearchToolFactory(
            run_id=run_id,
            market_service=self._market_service,
            metrics_service=self._metrics_service,
            analysis_repository=self._repository,
        ).create_tools()

        try:
            async with self._runner_factory(tools) as runner:
                analysis = await runner.run(run.user_query, run.thread_id)
            await asyncio.to_thread(
                self._repository.append_event,
                run_id,
                "AGENT_COMPLETED",
                "AI analysis completed",
                {},
                False,
            )
            validated = await asyncio.to_thread(self._validator.validate, run_id, analysis)
            record = AnalysisRecordMapper.to_record(validated)
            await asyncio.to_thread(self._repository.complete_run, run_id, record)
            await asyncio.to_thread(
                self._repository.append_event,
                run_id,
                "RUN_COMPLETED",
                "Research run completed",
                {"status": validated.status.value},
                True,
            )
        except Exception as exc:
            error_code = getattr(exc, "code", type(exc).__name__.upper())
            error_message = str(exc)[:500] or type(exc).__name__
            await asyncio.to_thread(
                self._repository.fail_run,
                run_id,
                error_code,
                error_message,
            )
            await asyncio.to_thread(
                self._repository.append_event,
                run_id,
                "RUN_FAILED",
                "Research run failed",
                {"error_code": error_code},
                True,
            )
