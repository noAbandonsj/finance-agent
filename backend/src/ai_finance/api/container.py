from dataclasses import dataclass

from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.akshare_provider import AkshareMarketDataProvider
from ai_finance.market.provider import MarketDataProvider
from ai_finance.market.service import MarketDataService
from ai_finance.records.database import Database
from ai_finance.records.repositories import AnalysisRepository, WatchlistRepository
from ai_finance.settings import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    market_service: MarketDataService
    metrics_service: MarketMetricsService
    database: Database
    analysis_repository: AnalysisRepository
    watchlist_repository: WatchlistRepository

    @classmethod
    def create(
        cls,
        settings: Settings,
        market_provider: MarketDataProvider | None = None,
        database: Database | None = None,
    ) -> "AppContainer":
        app_database = database or Database(settings.database_url)
        provider = market_provider or AkshareMarketDataProvider()
        return cls(
            settings=settings,
            market_service=MarketDataService(provider),
            metrics_service=MarketMetricsService(),
            database=app_database,
            analysis_repository=AnalysisRepository(app_database),
            watchlist_repository=WatchlistRepository(app_database),
        )
