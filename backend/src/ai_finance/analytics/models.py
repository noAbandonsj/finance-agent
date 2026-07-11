from datetime import date

from pydantic import BaseModel, ConfigDict


class MarketMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    observation_count: int
    start_date: date
    end_date: date
    returns: dict[str, float | None]
    moving_averages: dict[str, float | None]
    annualized_volatility: float | None
    max_drawdown: float | None
    volume_ratio: float | None
