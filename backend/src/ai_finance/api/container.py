from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass

from langchain_core.tools import BaseTool

from ai_finance.ai.model_gateway import ModelGateway
from ai_finance.ai.runner import LangChainResearchRunner
from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.akshare_provider import AkshareMarketDataProvider
from ai_finance.market.provider import MarketDataProvider
from ai_finance.market.service import MarketDataService
from ai_finance.records.database import Database
from ai_finance.records.repositories import AnalysisRepository, WatchlistRepository
from ai_finance.research.service import ResearchService, RunnerFactory, TaskRegistry
from ai_finance.settings import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    market_service: MarketDataService
    metrics_service: MarketMetricsService
    database: Database
    analysis_repository: AnalysisRepository
    watchlist_repository: WatchlistRepository
    research_service: ResearchService
    task_registry: TaskRegistry

    @classmethod
    def create(
        cls,
        settings: Settings,
        market_provider: MarketDataProvider | None = None,
        database: Database | None = None,
        runner_factory: RunnerFactory | None = None,
    ) -> "AppContainer":
        app_database = database or Database(settings.database_url)
        provider = market_provider or AkshareMarketDataProvider()
        market_service = MarketDataService(provider)
        metrics_service = MarketMetricsService()
        analysis_repository = AnalysisRepository(app_database)

        if runner_factory is None:

            @asynccontextmanager
            async def default_runner_factory(
                tools: Sequence[BaseTool],
            ) -> AsyncIterator[LangChainResearchRunner]:
                async with LangChainResearchRunner.create(
                    model_gateway=ModelGateway(settings),
                    model_name=settings.deepseek_deep_model,
                    tools=tools,
                    checkpoint_path=settings.checkpoint_path,
                ) as runner:
                    yield runner

            runner_factory = default_runner_factory

        return cls(
            settings=settings,
            market_service=market_service,
            metrics_service=metrics_service,
            database=app_database,
            analysis_repository=analysis_repository,
            watchlist_repository=WatchlistRepository(app_database),
            research_service=ResearchService(
                analysis_repository=analysis_repository,
                market_service=market_service,
                metrics_service=metrics_service,
                runner_factory=runner_factory,
                model_name=settings.deepseek_deep_model,
            ),
            task_registry=TaskRegistry(),
        )
