from typing import Protocol, runtime_checkable

from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_security_profile(self, symbol: str) -> SecurityProfile:
        raise NotImplementedError

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        raise NotImplementedError

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        raise NotImplementedError
