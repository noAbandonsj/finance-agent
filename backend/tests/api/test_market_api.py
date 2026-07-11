from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from ai_finance.api.app import create_app
from ai_finance.api.container import AppContainer
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.records.database import Database
from ai_finance.records.models import Base
from ai_finance.settings import Settings


class FixedProvider:
    def get_security_profile(self, symbol: str) -> SecurityProfile:
        security_type = SecurityType.ETF if symbol == "510300.SH" else SecurityType.STOCK
        return SecurityProfile(
            symbol=symbol,
            name="test security",
            security_type=security_type,
            exchange=symbol[-2:],
            provider="test",
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        profile = self.get_security_profile(symbol)
        return MarketSnapshot(
            symbol=symbol,
            name=profile.name,
            security_type=profile.security_type,
            last=4.2,
            previous_close=4.1,
            open=4.12,
            high=4.22,
            low=4.08,
            change_percent=2.44,
            volume=1000,
            amount=4200,
            market_time=datetime(2026, 7, 11, tzinfo=timezone.utc),
            timestamp_origin="retrieval_time",
            provider="test",
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        return [
            DailyBar(
                symbol=symbol,
                trading_date=date(2026, 7, day),
                open=float(day),
                high=float(day),
                low=float(day),
                close=float(day),
                volume=100,
                amount=1000,
                provider="test",
            )
            for day in range(1, min(trading_days, 3) + 1)
        ]


def make_client(tmp_path) -> TestClient:
    database = Database(f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(database.engine)
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'app.db'}", _env_file=None)
    container = AppContainer.create(
        settings=settings, market_provider=FixedProvider(), database=database
    )
    return TestClient(create_app(settings=settings, container=container))


def test_market_endpoints_return_normalized_contracts(tmp_path) -> None:
    client = make_client(tmp_path)

    profile = client.get("/api/market/600519/profile")
    snapshot = client.get("/api/market/510300/snapshot")
    bars = client.get("/api/market/600519/daily-bars", params={"trading_days": 60})

    assert profile.status_code == 200
    assert profile.json()["symbol"] == "600519.SH"
    assert snapshot.status_code == 200
    assert snapshot.json()["security_type"] == "ETF"
    assert bars.status_code == 200
    assert [row["trading_date"] for row in bars.json()] == [
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
    ]


def test_invalid_symbol_returns_problem_details(tmp_path) -> None:
    response = make_client(tmp_path).get("/api/market/abc/snapshot")

    assert response.status_code == 422
    assert response.json() == {
        "type": "about:blank",
        "title": "Invalid security symbol",
        "status": 422,
        "code": "INVALID_SYMBOL",
        "detail": "Unsupported symbol: abc",
    }


def test_rejects_out_of_range_history_window(tmp_path) -> None:
    response = make_client(tmp_path).get(
        "/api/market/600519/daily-bars", params={"trading_days": 4}
    )

    assert response.status_code == 422
