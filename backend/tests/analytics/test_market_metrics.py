from datetime import date, timedelta
from math import inf, nan, sqrt

import pytest

from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.models import DailyBar


def make_bars(closes: list[float], *, symbol: str = "600519.SH") -> list[DailyBar]:
    first_day = date(2026, 1, 5)
    return [
        DailyBar(
            symbol=symbol,
            trading_date=first_day + timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=float(100 + index),
            amount=None,
            provider="test",
        )
        for index, close in enumerate(closes)
    ]


def test_rejects_empty_history() -> None:
    with pytest.raises(ValueError, match="bars must not be empty"):
        MarketMetricsService().calculate("600519.SH", [])


@pytest.mark.parametrize(
    "invalid_close",
    [
        pytest.param(0.0, id="zero"),
        pytest.param(-1.0, id="negative"),
        pytest.param(nan, id="nan"),
        pytest.param(inf, id="positive-infinity"),
        pytest.param(-inf, id="negative-infinity"),
    ],
)
def test_rejects_non_positive_or_non_finite_closes(invalid_close: float) -> None:
    with pytest.raises(ValueError, match="close values must be finite and greater than zero"):
        MarketMetricsService().calculate("600519.SH", make_bars([invalid_close]))


def test_rejects_bar_symbol_mismatch() -> None:
    bars = make_bars([10.0, 11.0], symbol="510300.SH")

    with pytest.raises(ValueError, match="all bars must match the requested symbol"):
        MarketMetricsService().calculate("600519.SH", bars)


def test_rejects_mixed_bar_symbols() -> None:
    bars = make_bars([10.0, 11.0])
    bars[1] = bars[1].model_copy(update={"symbol": "510300.SH"})

    with pytest.raises(ValueError, match="all bars must match the requested symbol"):
        MarketMetricsService().calculate("600519.SH", bars)


def test_calculates_returns_moving_average_volatility_and_drawdown() -> None:
    bars = make_bars([10.0, 11.0, 9.0, 12.0, 12.5, 13.0])
    result = MarketMetricsService().calculate("600519.SH", bars)

    assert result.symbol == "600519.SH"
    assert result.observation_count == 6
    assert result.start_date == date(2026, 1, 5)
    assert result.end_date == date(2026, 1, 10)
    assert result.returns["5d"] == pytest.approx(0.30)
    assert result.moving_averages["5d"] == pytest.approx(11.5)
    assert result.max_drawdown == pytest.approx(9.0 / 11.0 - 1.0)
    assert result.annualized_volatility is not None


def test_uses_trailing_metric_windows_and_complete_history_for_drawdown() -> None:
    closes = [100.0, 50.0, 80.0, 90.0, 95.0, *map(float, range(100, 165))]
    volumes = [1000.0] * 45 + [10.0] * 20 + [40.0] * 5
    bars = [
        bar.model_copy(update={"volume": volume})
        for bar, volume in zip(make_bars(closes), volumes, strict=True)
    ]

    result = MarketMetricsService().calculate("600519.SH", bars)

    assert result.observation_count == 70
    assert result.returns["5d"] == pytest.approx(164.0 / 159.0 - 1.0)
    assert result.returns["20d"] == pytest.approx(164.0 / 144.0 - 1.0)
    assert result.returns["60d"] == pytest.approx(164.0 / 104.0 - 1.0)
    assert result.moving_averages == {
        "5d": pytest.approx(162.0),
        "20d": pytest.approx(154.5),
        "60d": pytest.approx(134.5),
    }
    assert result.volume_ratio == pytest.approx(4.0)
    assert result.max_drawdown == pytest.approx(-0.5)


def test_returns_none_when_history_is_insufficient() -> None:
    result = MarketMetricsService().calculate(
        "510300.SH", make_bars([4.0, 4.1], symbol="510300.SH")
    )

    assert result.returns == {"5d": None, "20d": None, "60d": None}
    assert result.moving_averages["5d"] is None
    assert result.annualized_volatility is None
    assert result.volume_ratio is None


def test_twenty_day_moving_average_needs_twenty_closes() -> None:
    result = MarketMetricsService().calculate(
        "600519.SH", make_bars([float(close) for close in range(1, 21)])
    )

    assert result.moving_averages["20d"] == pytest.approx(10.5)
    assert result.returns["20d"] is None


def test_twenty_day_return_needs_twenty_one_closes() -> None:
    result = MarketMetricsService().calculate(
        "600519.SH", make_bars([float(close) for close in range(1, 22)])
    )

    assert result.returns["20d"] == pytest.approx(20.0)


def test_sixty_day_moving_average_needs_sixty_closes() -> None:
    result = MarketMetricsService().calculate(
        "600519.SH", make_bars([float(close) for close in range(1, 61)])
    )

    assert result.moving_averages["60d"] == pytest.approx(30.5)
    assert result.returns["60d"] is None


def test_sixty_day_return_needs_sixty_one_closes() -> None:
    result = MarketMetricsService().calculate(
        "600519.SH", make_bars([float(close) for close in range(1, 62)])
    )

    assert result.returns["60d"] == pytest.approx(60.0)


def test_annualizes_sample_standard_deviation_of_daily_returns() -> None:
    result = MarketMetricsService().calculate("600519.SH", make_bars([10.0, 11.0, 9.0]))

    first_return = 11.0 / 10.0 - 1.0
    second_return = 9.0 / 11.0 - 1.0
    assert result.annualized_volatility == pytest.approx(
        abs(first_return - second_return) * sqrt(126)
    )


def test_volume_ratio_compares_latest_five_days_with_preceding_twenty() -> None:
    result = MarketMetricsService().calculate("600519.SH", make_bars([10.0] * 25))

    assert result.volume_ratio == pytest.approx(122.0 / 109.5)


def test_volume_ratio_is_none_when_preceding_mean_is_zero() -> None:
    bars = [
        bar.model_copy(update={"volume": 0.0 if index < 20 else 100.0})
        for index, bar in enumerate(make_bars([10.0] * 25))
    ]

    result = MarketMetricsService().calculate("600519.SH", bars)

    assert result.volume_ratio is None
