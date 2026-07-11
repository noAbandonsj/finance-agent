from fastapi.testclient import TestClient

from ai_finance.api.app import create_app
from ai_finance.api.container import AppContainer
from ai_finance.records.database import Database
from ai_finance.records.models import Base
from ai_finance.settings import Settings

from .test_market_api import FixedProvider


def make_client(tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    database = Database(database_url)
    Base.metadata.create_all(database.engine)
    settings = Settings(database_url=database_url, _env_file=None)
    container = AppContainer.create(
        settings=settings, market_provider=FixedProvider(), database=database
    )
    return TestClient(create_app(settings=settings, container=container))


def test_watchlist_create_is_idempotent_and_delete_uses_canonical_symbol(tmp_path) -> None:
    client = make_client(tmp_path)

    first = client.post("/api/watchlist", json={"symbol": "600519", "note": "focus"})
    second = client.post("/api/watchlist", json={"symbol": "600519.SH", "note": "ignored"})
    listed = client.get("/api/watchlist")
    deleted = client.delete("/api/watchlist/600519.SH")

    assert first.status_code == 201
    assert first.json()["symbol"] == "600519.SH"
    assert second.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["note"] == "focus"
    assert deleted.status_code == 204
    assert client.get("/api/watchlist").json() == []


def test_watchlist_rejects_invalid_symbol(tmp_path) -> None:
    response = make_client(tmp_path).post("/api/watchlist", json={"symbol": "700000"})

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SYMBOL"


def test_delete_missing_watchlist_item_returns_problem_details(tmp_path) -> None:
    response = make_client(tmp_path).delete("/api/watchlist/600519.SH")

    assert response.status_code == 404
    assert response.json()["code"] == "WATCHLIST_ITEM_NOT_FOUND"
