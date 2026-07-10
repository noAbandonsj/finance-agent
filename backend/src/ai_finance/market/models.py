from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SecurityType(StrEnum):
    STOCK = "STOCK"
    ETF = "ETF"


class SecurityProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    security_type: SecurityType
    exchange: str
    provider: str
    retrieved_at: datetime


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    security_type: SecurityType
    last: float
    previous_close: float | None
    open: float | None
    high: float | None
    low: float | None
    change_percent: float | None
    volume: float | None
    amount: float | None
    market_time: datetime
    timestamp_origin: str
    provider: str
    retrieved_at: datetime


class DailyBar(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float | None
    provider: str
