from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import pytest

from ai_finance.market.akshare_provider import AkshareMarketDataProvider
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.market.provider import MarketDataProvider
from ai_finance.market.service import MarketDataService
from ai_finance.shared.errors import ProviderUnavailableError, SecurityNotFoundError


FIXED_NOW = datetime(2026, 1, 10, 8, 30, tzinfo=timezone.utc)


def _stock_spot_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "代码": "600519",
                "名称": "贵州茅台",
                "最新价": "1,650.50",
                "昨收": "1640",
                "今开": "-",
                "最高": "1666.0",
                "最低": "",
                "涨跌幅": "0.64",
                "成交量": "12,345",
                "成交额": float("nan"),
            },
            {
                "代码": "510300",
                "名称": "stock table duplicate",
                "最新价": "1",
                "昨收": "1",
                "今开": "1",
                "最高": "1",
                "最低": "1",
                "涨跌幅": "0",
                "成交量": "1",
                "成交额": "1",
            },
        ]
    )


def _etf_spot_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "代码": "510300",
                "名称": "沪深300ETF",
                "最新价": "3.912",
                "昨收": "3.900",
                "开盘价": "3.890",
                "最高价": "3.930",
                "最低价": "3.880",
                "涨跌幅": "0.31",
                "成交量": "98,765",
                "成交额": "456789.5",
            }
        ]
    )


def _history_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "日期": "2026-01-03",
                "开盘": "12.0",
                "最高": "13.0",
                "最低": "11.5",
                "收盘": "12.5",
                "成交量": "3,000",
                "成交额": "-",
            },
            {
                "日期": "2026-01-01",
                "开盘": "10.0",
                "最高": "11.0",
                "最低": "9.5",
                "收盘": "10.5",
                "成交量": "1,000",
                "成交额": "10000",
            },
            {
                "日期": "2026-01-02",
                "开盘": "11.0",
                "最高": "12.0",
                "最低": "10.5",
                "收盘": "11.5",
                "成交量": "2,000",
                "成交额": "20000",
            },
        ]
    )


class FakeAkshare:
    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()
        self.history_arguments: dict[str, dict[str, Any]] = {}

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        self.calls["stock_spot"] += 1
        return _stock_spot_frame().copy()

    def fund_etf_spot_em(self) -> pd.DataFrame:
        self.calls["etf_spot"] += 1
        return _etf_spot_frame().copy()

    def stock_zh_a_hist(self, **kwargs: Any) -> pd.DataFrame:
        self.calls["stock_history"] += 1
        self.history_arguments["stock"] = kwargs
        return _history_frame().copy()

    def fund_etf_hist_em(self, **kwargs: Any) -> pd.DataFrame:
        self.calls["etf_history"] += 1
        self.history_arguments["etf"] = kwargs
        return _history_frame().copy()


def _provider(
    client: FakeAkshare,
    *,
    monotonic: Callable[[], float] = lambda: 0.0,
    sleeper: Callable[[float], None] = lambda _seconds: None,
) -> AkshareMarketDataProvider:
    return AkshareMarketDataProvider(
        client,
        monotonic=monotonic,
        sleeper=sleeper,
        now=lambda: FIXED_NOW,
    )


def test_provider_satisfies_runtime_checkable_contract() -> None:
    assert isinstance(_provider(FakeAkshare()), MarketDataProvider)


def test_profiles_classify_stocks_and_prefer_an_exact_etf_match() -> None:
    provider = _provider(FakeAkshare())

    stock = provider.get_security_profile("600519")
    etf = provider.get_security_profile("510300.SH")

    assert stock == SecurityProfile(
        symbol="600519.SH",
        name="贵州茅台",
        security_type=SecurityType.STOCK,
        exchange="SH",
        provider="akshare",
        retrieved_at=FIXED_NOW,
    )
    assert etf == SecurityProfile(
        symbol="510300.SH",
        name="沪深300ETF",
        security_type=SecurityType.ETF,
        exchange="SH",
        provider="akshare",
        retrieved_at=FIXED_NOW,
    )


def test_snapshot_normalizes_numbers_and_nullable_fields() -> None:
    snapshot = _provider(FakeAkshare()).get_market_snapshot("600519.sh")

    assert snapshot == MarketSnapshot(
        symbol="600519.SH",
        name="贵州茅台",
        security_type=SecurityType.STOCK,
        last=1650.5,
        previous_close=1640.0,
        open=None,
        high=1666.0,
        low=None,
        change_percent=0.64,
        volume=12345.0,
        amount=None,
        market_time=FIXED_NOW,
        timestamp_origin="retrieval_time",
        provider="akshare",
        retrieved_at=FIXED_NOW,
    )


def test_etf_snapshot_uses_etf_column_names() -> None:
    snapshot = _provider(FakeAkshare()).get_market_snapshot("510300")

    assert snapshot.security_type is SecurityType.ETF
    assert snapshot.open == 3.89
    assert snapshot.high == 3.93
    assert snapshot.low == 3.88


def test_spot_tables_are_cached_together_for_30_seconds() -> None:
    client = FakeAkshare()
    current_time = [100.0]
    provider = _provider(client, monotonic=lambda: current_time[0])

    provider.get_security_profile("600519")
    provider.get_market_snapshot("510300")
    current_time[0] += 29.999
    provider.get_security_profile("510300")

    assert client.calls["stock_spot"] == 1
    assert client.calls["etf_spot"] == 1

    current_time[0] += 0.001
    provider.get_security_profile("600519")

    assert client.calls["stock_spot"] == 2
    assert client.calls["etf_spot"] == 2


def test_stock_daily_bars_use_stock_history_and_return_latest_rows_ascending() -> None:
    client = FakeAkshare()
    bars = _provider(client).get_daily_bars("sh600519", trading_days=2)

    assert bars == [
        DailyBar(
            symbol="600519.SH",
            trading_date=date(2026, 1, 2),
            open=11.0,
            high=12.0,
            low=10.5,
            close=11.5,
            volume=2000.0,
            amount=20000.0,
            provider="akshare",
        ),
        DailyBar(
            symbol="600519.SH",
            trading_date=date(2026, 1, 3),
            open=12.0,
            high=13.0,
            low=11.5,
            close=12.5,
            volume=3000.0,
            amount=None,
            provider="akshare",
        ),
    ]
    assert client.calls["stock_history"] == 1
    assert client.calls["etf_history"] == 0
    _assert_history_arguments(client.history_arguments["stock"], raw_code="600519")


def test_etf_daily_bars_use_etf_history() -> None:
    client = FakeAkshare()
    bars = _provider(client).get_daily_bars("510300", trading_days=1)

    assert [bar.trading_date for bar in bars] == [date(2026, 1, 3)]
    assert all(bar.symbol == "510300.SH" for bar in bars)
    assert client.calls["etf_history"] == 1
    assert client.calls["stock_history"] == 0
    _assert_history_arguments(client.history_arguments["etf"], raw_code="510300")


class WideningHistoryAkshare(FakeAkshare):
    def __init__(self, *, older_rows_available: bool) -> None:
        super().__init__()
        self.older_rows_available = older_rows_available
        self.stock_history_requests: list[dict[str, Any]] = []

    def stock_zh_a_hist(self, **kwargs: Any) -> pd.DataFrame:
        self.calls["stock_history"] += 1
        self.stock_history_requests.append(kwargs)
        frame = _history_frame()
        if not self.older_rows_available or self.calls["stock_history"] == 1:
            return frame.copy()
        older_rows = pd.DataFrame(
            [
                {
                    "日期": "2025-12-30",
                    "开盘": "8.0",
                    "最高": "9.0",
                    "最低": "7.5",
                    "收盘": "8.5",
                    "成交量": "800",
                    "成交额": "8000",
                },
                {
                    "日期": "2025-12-31",
                    "开盘": "9.0",
                    "最高": "10.0",
                    "最低": "8.5",
                    "收盘": "9.5",
                    "成交量": "900",
                    "成交额": "9000",
                },
            ]
        )
        return pd.concat([frame, older_rows], ignore_index=True)


def test_daily_bars_widen_history_window_until_enough_rows_are_available() -> None:
    client = WideningHistoryAkshare(older_rows_available=True)

    bars = _provider(client).get_daily_bars("600519", trading_days=4)

    assert [bar.trading_date for bar in bars] == [
        date(2025, 12, 31),
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert len(client.stock_history_requests) == 2
    initial_request, wider_request = client.stock_history_requests
    assert wider_request["start_date"] < initial_request["start_date"]
    assert wider_request["end_date"] == initial_request["end_date"]


def test_daily_bars_stop_widening_at_earliest_supported_history() -> None:
    client = WideningHistoryAkshare(older_rows_available=False)

    bars = _provider(client).get_daily_bars("600519", trading_days=10)

    assert [bar.trading_date for bar in bars] == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert client.stock_history_requests[-1]["start_date"] == "19900101"
    assert len(client.stock_history_requests) <= 10


@pytest.mark.parametrize("trading_days", [0, -1])
def test_daily_bars_reject_non_positive_counts_before_provider_calls(
    trading_days: int,
) -> None:
    client = FakeAkshare()

    with pytest.raises(ValueError, match="trading_days must be greater than zero"):
        _provider(client).get_daily_bars("600519", trading_days)

    assert client.calls == Counter()


def _assert_history_arguments(arguments: dict[str, Any], *, raw_code: str) -> None:
    assert arguments["symbol"] == raw_code
    assert arguments["period"] == "daily"
    assert arguments["adjust"] == "qfq"
    start = datetime.strptime(arguments["start_date"], "%Y%m%d").date()
    end = datetime.strptime(arguments["end_date"], "%Y%m%d").date()
    assert end == FIXED_NOW.date()
    assert end - start >= timedelta(days=2)


@pytest.mark.parametrize(
    "operation",
    [
        lambda provider: provider.get_security_profile("159915"),
        lambda provider: provider.get_market_snapshot("159915"),
        lambda provider: provider.get_daily_bars("159915", 5),
    ],
)
def test_missing_security_raises_typed_error(operation: Callable[[Any], object]) -> None:
    with pytest.raises(SecurityNotFoundError) as error:
        operation(_provider(FakeAkshare()))

    assert error.value.code == "SECURITY_NOT_FOUND"
    assert error.value.symbol == "159915.SZ"


class FailingStockSpotAkshare(FakeAkshare):
    def __init__(self, failures: list[Exception]) -> None:
        super().__init__()
        self.failures = failures

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        self.calls["stock_spot"] += 1
        if self.failures:
            raise self.failures.pop(0)
        return _stock_spot_frame().copy()


class MissingSpotColumnAkshare(FakeAkshare):
    def __init__(self, missing_column: str | None) -> None:
        super().__init__()
        self.missing_column = missing_column

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        self.calls["stock_spot"] += 1
        frame = _stock_spot_frame()
        if self.missing_column is not None:
            frame = frame.drop(columns=[self.missing_column])
        return frame.copy()


@pytest.mark.parametrize("missing_column", ["代码", "名称", "最新价"])
def test_invalid_spot_schema_raises_provider_error_without_caching(
    missing_column: str,
) -> None:
    client = MissingSpotColumnAkshare(missing_column)
    provider = _provider(client)

    with pytest.raises(ProviderUnavailableError) as error:
        provider.get_security_profile("600519")

    assert error.value.code == "PROVIDER_UNAVAILABLE"
    client.missing_column = None
    assert provider.get_security_profile("600519").symbol == "600519.SH"
    assert client.calls["stock_spot"] == 2
    assert client.calls["etf_spot"] == 2


def test_provider_retries_a_failed_akshare_call_once() -> None:
    client = FailingStockSpotAkshare([ConnectionError("temporary")])
    sleeps: list[float] = []

    profile = _provider(client, sleeper=sleeps.append).get_security_profile("600519")

    assert profile.symbol == "600519.SH"
    assert client.calls["stock_spot"] == 2
    assert sleeps == [0.25]


def test_provider_unavailable_error_chains_the_original_failure() -> None:
    original = ConnectionError("first failure")
    client = FailingStockSpotAkshare([original, TimeoutError("second failure")])
    sleeps: list[float] = []

    with pytest.raises(ProviderUnavailableError) as error:
        _provider(client, sleeper=sleeps.append).get_market_snapshot("600519")

    assert error.value.code == "PROVIDER_UNAVAILABLE"
    assert error.value.__cause__ is original
    assert client.calls["stock_spot"] == 2
    assert sleeps == [0.25]


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def get_security_profile(self, symbol: str) -> SecurityProfile:
        self.calls.append(("profile", symbol))
        return SecurityProfile(
            symbol=symbol,
            name="name",
            security_type=SecurityType.STOCK,
            exchange=symbol[-2:],
            provider="recording",
            retrieved_at=FIXED_NOW,
        )

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        self.calls.append(("snapshot", symbol))
        return MarketSnapshot(
            symbol=symbol,
            name="name",
            security_type=SecurityType.STOCK,
            last=1.0,
            previous_close=None,
            open=None,
            high=None,
            low=None,
            change_percent=None,
            volume=None,
            amount=None,
            market_time=FIXED_NOW,
            timestamp_origin="retrieval_time",
            provider="recording",
            retrieved_at=FIXED_NOW,
        )

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        self.calls.append(("bars", symbol, trading_days))
        return []


def test_market_service_normalizes_symbols_before_delegating() -> None:
    recording_provider = RecordingProvider()
    service = MarketDataService(recording_provider)

    service.get_security_profile("sh600519")
    service.get_market_snapshot("600519.sh")
    service.get_daily_bars(" 600519 ", 20)

    assert recording_provider.calls == [
        ("profile", "600519.SH"),
        ("snapshot", "600519.SH"),
        ("bars", "600519.SH", 20),
    ]


@pytest.mark.parametrize("trading_days", [0, -20])
def test_market_service_rejects_non_positive_counts_before_delegating(
    trading_days: int,
) -> None:
    recording_provider = RecordingProvider()
    service = MarketDataService(recording_provider)

    with pytest.raises(ValueError, match="trading_days must be greater than zero"):
        service.get_daily_bars("600519", trading_days)

    assert recording_provider.calls == []
