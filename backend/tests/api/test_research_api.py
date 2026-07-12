import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from langchain_core.tools import BaseTool

from ai_finance.api.app import create_app
from ai_finance.api.container import AppContainer
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile, SecurityType
from ai_finance.records.database import Database
from ai_finance.records.models import Base
from ai_finance.settings import Settings


class FixedProvider:
    def get_security_profile(self, symbol: str) -> SecurityProfile:
        return SecurityProfile(
            symbol=symbol,
            name="Test Security",
            security_type=SecurityType.STOCK,
            exchange="SH",
            provider="test",
            retrieved_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        )

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
            name="Test Security",
            security_type=SecurityType.STOCK,
            last=10,
            previous_close=9.9,
            open=9.9,
            high=10.1,
            low=9.8,
            change_percent=1,
            volume=100,
            amount=1000,
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
            for day in range(1, 11)
        ]


class FixedRunner:
    def __init__(self, tools: Sequence[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    async def run(self, user_query: str, thread_id: str) -> str:
        await self._tools["get_market_snapshot"].ainvoke({"symbol": "600519"})
        await self._tools["calculate_market_metrics"].ainvoke(
            {"symbol": "600519", "trading_days": 10}
        )
        return "# Test Security\n\nBalanced."


@asynccontextmanager
async def fixed_runner_factory(tools: Sequence[BaseTool]) -> AsyncIterator[FixedRunner]:
    yield FixedRunner(tools)


def make_client(tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    database = Database(database_url)
    Base.metadata.create_all(database.engine)
    settings = Settings(database_url=database_url, _env_file=None)
    container = AppContainer.create(
        settings=settings,
        market_provider=FixedProvider(),
        database=database,
        runner_factory=fixed_runner_factory,
    )
    return TestClient(create_app(settings=settings, container=container))


def test_create_list_detail_and_resume_event_stream(tmp_path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/api/research/runs",
            json={"symbol": "600519", "question": "Analyze this security"},
        )
        assert created.status_code == 202
        body = created.json()
        assert body["event_url"] == f"/api/research/runs/{body['run_id']}/events"

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            detail = client.get(f"/api/research/runs/{body['run_id']}")
            if detail.json()["status"] != "RUNNING":
                break
            time.sleep(0.02)

        assert detail.json()["status"] == "COMPLETE"
        assert detail.json()["result"]["report_markdown"].startswith("# Test Security")
        assert client.get("/api/research/runs").json()[0]["id"] == body["run_id"]

        events = client.get(
            body["event_url"],
            headers={"Last-Event-ID": "2"},
        )
        assert events.status_code == 200
        assert "event: TOOL_STARTED" in events.text
        assert "event: AGENT_COMPLETED" in events.text
        assert "id: 1" not in events.text

        exhausted = client.get(
            body["event_url"],
            headers={"Last-Event-ID": "8"},
        )
        assert exhausted.status_code == 200
        assert exhausted.text == ""


def test_research_run_rejects_invalid_symbol(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/research/runs",
            json={"symbol": "abc", "question": "Analyze"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SYMBOL"
