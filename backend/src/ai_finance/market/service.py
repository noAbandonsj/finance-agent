from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile
from ai_finance.market.provider import MarketDataProvider
from ai_finance.market.symbols import normalize_symbol


class MarketDataService:
    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    def get_security_profile(self, symbol: str) -> SecurityProfile:
        return self.provider.get_security_profile(normalize_symbol(symbol))

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        return self.provider.get_market_snapshot(normalize_symbol(symbol))

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        return self.provider.get_daily_bars(normalize_symbol(symbol), trading_days)
