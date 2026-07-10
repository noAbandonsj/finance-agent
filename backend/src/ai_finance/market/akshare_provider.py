import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from typing import Any, Protocol, TypeVar, cast

import pandas as pd

from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.market.symbols import normalize_symbol
from ai_finance.shared.errors import ProviderUnavailableError, SecurityNotFoundError


class _AkshareClient(Protocol):
    def stock_zh_a_spot_em(self) -> pd.DataFrame: ...

    def fund_etf_spot_em(self) -> pd.DataFrame: ...

    def stock_zh_a_hist(self, **kwargs: Any) -> pd.DataFrame: ...

    def fund_etf_hist_em(self, **kwargs: Any) -> pd.DataFrame: ...


@dataclass(frozen=True, slots=True)
class _SpotRecord:
    symbol: str
    raw_code: str
    security_type: SecurityType
    values: Mapping[str, object]


_T = TypeVar("_T")


class AkshareMarketDataProvider:
    provider_name = "akshare"

    def __init__(
        self,
        client: _AkshareClient | None = None,
        *,
        cache_ttl_seconds: float = 30.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if client is None:
            import akshare

            client = cast(_AkshareClient, akshare)

        self._client = client
        self._cache_ttl_seconds = cache_ttl_seconds
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._cache_lock = Lock()
        self._cache_loaded_at: float | None = None
        self._stock_records: dict[str, _SpotRecord] = {}
        self._etf_records: dict[str, _SpotRecord] = {}

    def get_security_profile(self, symbol: str) -> SecurityProfile:
        canonical_symbol = normalize_symbol(symbol)
        record = self._find_record(canonical_symbol)
        retrieved_at = self._now()
        try:
            return SecurityProfile(
                symbol=canonical_symbol,
                name=self._required_text(record.values.get("名称"), "名称"),
                security_type=record.security_type,
                exchange=canonical_symbol.rsplit(".", 1)[1],
                provider=self.provider_name,
                retrieved_at=retrieved_at,
            )
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailableError("AKShare returned an invalid security profile") from exc

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        canonical_symbol = normalize_symbol(symbol)
        record = self._find_record(canonical_symbol)
        retrieved_at = self._now()
        try:
            return MarketSnapshot(
                symbol=canonical_symbol,
                name=self._required_text(record.values.get("名称"), "名称"),
                security_type=record.security_type,
                last=self._required_float(record.values.get("最新价"), "最新价"),
                previous_close=self._optional_float(record.values.get("昨收")),
                open=self._optional_float(self._first_value(record.values, "今开", "开盘价")),
                high=self._optional_float(self._first_value(record.values, "最高", "最高价")),
                low=self._optional_float(self._first_value(record.values, "最低", "最低价")),
                change_percent=self._optional_float(record.values.get("涨跌幅")),
                volume=self._optional_float(record.values.get("成交量")),
                amount=self._optional_float(record.values.get("成交额")),
                market_time=retrieved_at,
                timestamp_origin="retrieval_time",
                provider=self.provider_name,
                retrieved_at=retrieved_at,
            )
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailableError("AKShare returned an invalid market snapshot") from exc

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        canonical_symbol = normalize_symbol(symbol)
        record = self._find_record(canonical_symbol)
        end = self._now().date()
        calendar_days = max(30, trading_days * 2)
        arguments = {
            "symbol": record.raw_code,
            "period": "daily",
            "start_date": (end - timedelta(days=calendar_days)).strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d"),
            "adjust": "qfq",
        }
        if record.security_type is SecurityType.ETF:
            frame = self._call_with_retry(self._client.fund_etf_hist_em, **arguments)
        else:
            frame = self._call_with_retry(self._client.stock_zh_a_hist, **arguments)

        try:
            bars = [self._daily_bar(canonical_symbol, row) for row in frame.to_dict("records")]
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailableError("AKShare returned invalid daily history") from exc

        bars.sort(key=lambda bar: bar.trading_date)
        return bars[-trading_days:]

    def _find_record(self, canonical_symbol: str) -> _SpotRecord:
        stock_records, etf_records = self._get_spot_records()
        record = etf_records.get(canonical_symbol) or stock_records.get(canonical_symbol)
        if record is None:
            raise SecurityNotFoundError(canonical_symbol)
        return record

    def _get_spot_records(
        self,
    ) -> tuple[dict[str, _SpotRecord], dict[str, _SpotRecord]]:
        with self._cache_lock:
            current_time = self._monotonic()
            if (
                self._cache_loaded_at is not None
                and current_time - self._cache_loaded_at < self._cache_ttl_seconds
            ):
                return self._stock_records, self._etf_records

            stock_frame = self._call_with_retry(self._client.stock_zh_a_spot_em)
            etf_frame = self._call_with_retry(self._client.fund_etf_spot_em)
            try:
                stock_records = self._normalize_spot_frame(stock_frame, SecurityType.STOCK)
                etf_records = self._normalize_spot_frame(etf_frame, SecurityType.ETF)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ProviderUnavailableError("AKShare returned invalid spot data") from exc

            self._stock_records = stock_records
            self._etf_records = etf_records
            self._cache_loaded_at = self._monotonic()
            return self._stock_records, self._etf_records

    def _normalize_spot_frame(
        self,
        frame: pd.DataFrame,
        security_type: SecurityType,
    ) -> dict[str, _SpotRecord]:
        records: dict[str, _SpotRecord] = {}
        for values in frame.to_dict("records"):
            raw_code = self._code_text(values.get("代码"))
            try:
                canonical_symbol = normalize_symbol(raw_code)
            except ValueError:
                continue
            records[canonical_symbol] = _SpotRecord(
                symbol=canonical_symbol,
                raw_code=raw_code,
                security_type=security_type,
                values=values,
            )
        return records

    def _daily_bar(self, canonical_symbol: str, row: Mapping[str, object]) -> DailyBar:
        return DailyBar(
            symbol=canonical_symbol,
            trading_date=self._trading_date(row["日期"]),
            open=self._required_float(row.get("开盘"), "开盘"),
            high=self._required_float(row.get("最高"), "最高"),
            low=self._required_float(row.get("最低"), "最低"),
            close=self._required_float(row.get("收盘"), "收盘"),
            volume=self._required_float(row.get("成交量"), "成交量"),
            amount=self._optional_float(row.get("成交额")),
            provider=self.provider_name,
        )

    def _call_with_retry(self, operation: Callable[..., _T], **kwargs: object) -> _T:
        try:
            return operation(**kwargs)
        except Exception as original_error:
            self._sleeper(0.25)
            try:
                return operation(**kwargs)
            except Exception:
                operation_name = getattr(operation, "__name__", "AKShare operation")
                raise ProviderUnavailableError(
                    f"AKShare call failed after retry: {operation_name}"
                ) from original_error

    @staticmethod
    def _first_value(values: Mapping[str, object], *columns: str) -> object | None:
        for column in columns:
            if column in values:
                return values[column]
        return None

    @staticmethod
    def _code_text(value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        if isinstance(value, int):
            return f"{value:06d}"
        if isinstance(value, float) and math.isfinite(value) and value.is_integer():
            return f"{int(value):06d}"
        return str(value).strip()

    @classmethod
    def _required_float(cls, value: object, column: str) -> float:
        converted = cls._optional_float(value)
        if converted is None:
            raise ValueError(f"AKShare column {column} is missing")
        return converted

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value in {"-", "--"}:
                return None
            value = value.replace(",", "")
        converted = float(value)
        if math.isnan(converted):
            return None
        return converted

    @staticmethod
    def _required_text(value: object, column: str) -> str:
        if value is None or pd.isna(value):
            raise ValueError(f"AKShare column {column} is missing")
        converted = str(value).strip()
        if not converted or converted == "-":
            raise ValueError(f"AKShare column {column} is missing")
        return converted

    @staticmethod
    def _trading_date(value: object) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()
