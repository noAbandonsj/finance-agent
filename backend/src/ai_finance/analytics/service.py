from math import sqrt
from statistics import stdev

from ai_finance.analytics.models import MarketMetrics
from ai_finance.market.models import DailyBar


class MarketMetricsService:
    def calculate(self, symbol: str, bars: list[DailyBar]) -> MarketMetrics:
        closes = [bar.close for bar in bars]
        daily_returns = [
            current_close / previous_close - 1.0
            for previous_close, current_close in zip(closes, closes[1:], strict=False)
        ]

        running_max = closes[0]
        drawdowns: list[float] = []
        for close in closes:
            running_max = max(running_max, close)
            drawdowns.append(close / running_max - 1.0)

        volume_ratio = None
        if len(bars) >= 25:
            preceding_mean = sum(bar.volume for bar in bars[-25:-5]) / 20
            latest_mean = sum(bar.volume for bar in bars[-5:]) / 5
            if preceding_mean != 0:
                volume_ratio = latest_mean / preceding_mean

        return MarketMetrics(
            symbol=symbol,
            observation_count=len(bars),
            start_date=bars[0].trading_date,
            end_date=bars[-1].trading_date,
            returns={
                "5d": closes[-1] / closes[-6] - 1.0 if len(closes) >= 6 else None,
                "20d": closes[-1] / closes[-21] - 1.0 if len(closes) >= 21 else None,
                "60d": closes[-1] / closes[-61] - 1.0 if len(closes) >= 61 else None,
            },
            moving_averages={
                "5d": sum(closes[-5:]) / 5 if len(closes) >= 5 else None,
                "20d": sum(closes[-20:]) / 20 if len(closes) >= 20 else None,
                "60d": sum(closes[-60:]) / 60 if len(closes) >= 60 else None,
            },
            annualized_volatility=(stdev(daily_returns) * sqrt(252) if len(closes) >= 3 else None),
            max_drawdown=min(drawdowns),
            volume_ratio=volume_ratio,
        )
