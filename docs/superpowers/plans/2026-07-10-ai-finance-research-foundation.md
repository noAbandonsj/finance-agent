# AI Finance Research Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Vue and FastAPI application in which a DeepSeek-backed LangChain agent autonomously calls read-only AKShare and quantitative tools to produce traceable A-share and ETF research.

**Architecture:** A modular FastAPI monolith exposes market, watchlist, history, research, and SSE endpoints. LangChain `create_agent` uses DeepSeek through an OpenAI-compatible model gateway, while SQLite stores business records and a separate SQLite checkpointer stores agent state. Vue provides the operational research workspace.

**Tech Stack:** Existing Python 3.13.7, uv 0.11.2, Node.js 24.11.1, npm 11.6.2, FastAPI, LangChain, DeepSeek, AKShare, pandas, NumPy, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, Vue 3, TypeScript, Vite, Pinia, Element Plus, ECharts, pytest, Vitest, Playwright.

## Global Constraints

- Use `D:\Pathon\python.exe`; run `uv venv --python D:\Pathon\python.exe` and never let uv download a different interpreter.
- Commit `uv.lock` and `frontend/package-lock.json`.
- Bind the backend to `127.0.0.1`; do not implement authentication or remote deployment.
- Runtime model calls require a real `DEEPSEEK_API_KEY`; runtime market calls require real AKShare data.
- Test doubles and recorded market frames may exist only under test directories.
- Support A-share stocks and exchange-traded funds, latest snapshots, and daily history only.
- Keep `data/app.db` and `data/checkpoints.db` separate.
- Do not add Docker, Redis, PostgreSQL, Kafka, Celery, microservices, brokerage connectivity, portfolio accounting, or executable order endpoints.
- Use test-first development for every behavior: observe the intended failure before writing production code.
- Use ASCII in source code unless Chinese UI text or provider column names require Unicode.

---

## File Map

```text
.env.example                         documented local environment variables
.gitignore                           local secrets, databases, caches, build output
pyproject.toml                       uv workspace and shared tooling
backend/pyproject.toml               Python package and dependencies
backend/alembic.ini                  migration configuration
backend/alembic/                     business database migrations
backend/src/ai_finance/settings.py   typed local configuration
backend/src/ai_finance/api/          FastAPI app and routes
backend/src/ai_finance/market/       symbols, contracts, AKShare provider, service
backend/src/ai_finance/analytics/    deterministic market metrics
backend/src/ai_finance/records/      SQLAlchemy models and repositories
backend/src/ai_finance/ai/           model gateway, schemas, tools, agent runner
backend/src/ai_finance/research/     run lifecycle, validation, SSE events
backend/tests/                        unit, integration, and explicit live smoke tests
frontend/                             Vue application
scripts/dev.ps1                       local API and web startup
scripts/check.ps1                     complete verification command
data/.gitkeep                         local data directory marker
README.md                             setup and operation
```

### Task 1: Establish the uv-managed backend and health API

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `backend/pyproject.toml`
- Create: `backend/src/ai_finance/__init__.py`
- Create: `backend/src/ai_finance/settings.py`
- Create: `backend/src/ai_finance/api/app.py`
- Create: `backend/src/ai_finance/api/routes/health.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `Settings`, `get_settings()`, and `create_app(settings: Settings | None = None) -> FastAPI`.
- Produces: `GET /api/health` and `GET /api/config/status`.

- [ ] **Step 1: Create the uv manifests and local environment**

Root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["backend"]
```

`backend/pyproject.toml`:

```toml
[project]
name = "ai-finance-backend"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  "aiosqlite>=0.21,<1",
  "akshare>=1.18,<2",
  "alembic>=1.16,<2",
  "fastapi>=0.116,<1",
  "langchain>=1.1,<2",
  "langchain-openai>=1.0,<2",
  "langgraph-checkpoint-sqlite>=3,<4",
  "numpy>=2.3,<3",
  "pandas>=2.3,<3",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "sqlalchemy>=2.0.41,<3",
  "uvicorn[standard]>=0.35,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.4,<9",
  "pytest-asyncio>=1.0,<2",
  "pytest-cov>=6.2,<7",
  "respx>=0.22,<1",
  "ruff>=0.12,<1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ai_finance"]

[tool.pytest.ini_options]
addopts = "-q -m 'not live'"
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = ["live: calls paid or public external services"]

[tool.ruff]
line-length = 100
target-version = "py313"
```

Run:

```powershell
uv venv --python D:\Pathon\python.exe
uv sync --all-packages --all-extras
uv run python --version
```

Expected: the final command prints `Python 3.13.7`, and `uv.lock` is created.

- [ ] **Step 2: Write failing configuration and health tests**

```python
from fastapi.testclient import TestClient

from ai_finance.api.app import create_app
from ai_finance.settings import Settings


def test_config_status_never_returns_api_key() -> None:
    settings = Settings(deepseek_api_key="secret-value", _env_file=None)
    response = TestClient(create_app(settings)).get("/api/config/status")

    assert response.status_code == 200
    assert response.json() == {
        "model_configured": True,
        "default_model": "deepseek-v4-flash",
        "deep_model": "deepseek-v4-pro",
        "market_provider": "akshare",
    }
    assert "secret-value" not in response.text


def test_health_is_local_service_ready() -> None:
    response = TestClient(create_app(Settings(_env_file=None))).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-finance-backend"}
```

- [ ] **Step 3: Run the tests and verify the intended import failure**

Run: `uv run --project backend pytest backend/tests/test_health.py -v`

Expected: collection fails because `ai_finance.api.app` and `ai_finance.settings` do not exist.

- [ ] **Step 4: Implement settings and the two endpoints**

`settings.py` must define these fields and no secret-returning serializer:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-finance-backend"
    host: str = "127.0.0.1"
    port: int = 8000
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-v4-flash"
    deepseek_deep_model: str = "deepseek-v4-pro"
    database_url: str = "sqlite:///data/app.db"
    checkpoint_path: Path = Path("data/checkpoints.db")
    market_provider: str = "akshare"

    @property
    def model_configured(self) -> bool:
        return self.deepseek_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`create_app` must include routers under `/api`, store settings on `app.state`, and expose only the non-secret status fields asserted by the tests. The module must end with `app = create_app()` so Uvicorn can load `ai_finance.api.app:app`.

- [ ] **Step 5: Verify backend foundation**

Run:

```powershell
uv run --project backend pytest backend/tests/test_health.py -v
uv run --project backend ruff check backend/src backend/tests
```

Expected: both tests pass and Ruff reports no errors.

- [ ] **Step 6: Add local ignore and environment templates**

`.env.example`:

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_DEEP_MODEL=deepseek-v4-pro
DATABASE_URL=sqlite:///data/app.db
CHECKPOINT_PATH=data/checkpoints.db
```

`.gitignore` must ignore `.env`, `.venv/`, `data/*.db`, Python caches, `.pytest_cache/`, `.ruff_cache/`, `frontend/node_modules/`, `frontend/dist/`, and Playwright output while retaining `data/.gitkeep`.

- [ ] **Step 7: Commit the foundation**

```powershell
git add .gitignore .env.example pyproject.toml uv.lock backend
git commit -m "chore: initialize local backend foundation"
```

### Task 2: Implement canonical symbols and the AKShare provider

**Files:**
- Create: `backend/src/ai_finance/shared/errors.py`
- Create: `backend/src/ai_finance/market/models.py`
- Create: `backend/src/ai_finance/market/symbols.py`
- Create: `backend/src/ai_finance/market/provider.py`
- Create: `backend/src/ai_finance/market/akshare_provider.py`
- Create: `backend/src/ai_finance/market/service.py`
- Create: `backend/tests/market/test_symbols.py`
- Create: `backend/tests/market/test_akshare_provider.py`

**Interfaces:**
- Produces: `normalize_symbol(value: str) -> str`.
- Produces: `MarketDataProvider.get_security_profile`, `.get_market_snapshot`, and `.get_daily_bars`.
- Produces: normalized `SecurityProfile`, `MarketSnapshot`, and `DailyBar` Pydantic models.

- [ ] **Step 1: Write failing symbol and provider-contract tests**

The tests must prove all of these cases:

```python
import pytest

from ai_finance.market.symbols import normalize_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("600519", "600519.SH"),
        ("600519.sh", "600519.SH"),
        ("sz000001", "000001.SZ"),
        ("510300", "510300.SH"),
        ("159915", "159915.SZ"),
        ("920001", "920001.BJ"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12345", "700000", "600519.HK"])
def test_rejects_unsupported_symbol(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_symbol(raw)
```

Provider tests must inject an object whose `stock_zh_a_spot_em`, `fund_etf_spot_em`, `stock_zh_a_hist`, and `fund_etf_hist_em` methods return fixed pandas DataFrames. Assert stock and ETF classification, numeric conversion, provider name, canonical symbol, ascending daily dates, and a typed not-found error.

- [ ] **Step 2: Run tests to verify missing modules**

Run: `uv run --project backend pytest backend/tests/market -v`

Expected: tests fail because the market package has not been implemented.

- [ ] **Step 3: Implement market contracts**

Use these exact model fields:

```python
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
```

Define `MarketDataProvider` as a runtime-checkable Protocol with these exact signatures and define `ProviderUnavailableError` and `SecurityNotFoundError` with stable `code` values:

```python
@runtime_checkable
class MarketDataProvider(Protocol):
    def get_security_profile(self, symbol: str) -> SecurityProfile:
        raise NotImplementedError

    def get_market_snapshot(self, symbol: str) -> MarketSnapshot:
        raise NotImplementedError

    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]:
        raise NotImplementedError
```

- [ ] **Step 4: Implement symbol inference and AKShare normalization**

`normalize_symbol` must remove whitespace, accept optional exchange prefixes or suffixes, and infer exchanges as follows:

```text
SH: codes beginning with 5, 6, or 9
SZ: codes beginning with 0, 1, 2, or 3
BJ: codes beginning with 4, 8, or 92
```

The provider must:

- Call `stock_zh_a_spot_em()` and `fund_etf_spot_em()` for current tables.
- Cache the two normalized tables in memory for 30 seconds.
- Prefer an exact ETF-table match before a stock-table match.
- Use `stock_zh_a_hist(symbol=raw_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")` for stocks.
- Use `fund_etf_hist_em(symbol=raw_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")` for ETFs.
- Request enough calendar days to return the requested number of trading rows, sort ascending, then take the final `trading_days` rows.
- Convert `NaN`, `-`, and empty fields to `None` where the contract permits nulls.
- Set `timestamp_origin="retrieval_time"` because the snapshot tables do not provide a trustworthy exchange timestamp.
- Retry a failed AKShare call once after 250 milliseconds, then raise `ProviderUnavailableError` with the original exception chained.

- [ ] **Step 5: Verify provider behavior**

Run:

```powershell
uv run --project backend pytest backend/tests/market -v
uv run --project backend ruff check backend/src/ai_finance/market backend/tests/market
```

Expected: all market tests pass without network access.

- [ ] **Step 6: Commit market access**

```powershell
git add backend/src/ai_finance/market backend/src/ai_finance/shared backend/tests/market
git commit -m "feat: add AKShare market data provider"
```

### Task 3: Add deterministic quantitative metrics

**Files:**
- Create: `backend/src/ai_finance/analytics/models.py`
- Create: `backend/src/ai_finance/analytics/service.py`
- Create: `backend/tests/analytics/test_market_metrics.py`

**Interfaces:**
- Consumes: `list[DailyBar]` from Task 2.
- Produces: `MarketMetricsService.calculate(symbol: str, bars: list[DailyBar]) -> MarketMetrics`.

- [ ] **Step 1: Write failing metric tests**

Build deterministic daily bars and assert:

```python
from datetime import date, timedelta

import pytest

from ai_finance.analytics.service import MarketMetricsService
from ai_finance.market.models import DailyBar


def make_bars(closes: list[float]) -> list[DailyBar]:
    first_day = date(2026, 1, 5)
    return [
        DailyBar(
            symbol="600519.SH",
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


def test_calculates_returns_moving_average_volatility_and_drawdown() -> None:
    bars = make_bars([10.0, 11.0, 9.0, 12.0, 12.5, 13.0])
    result = MarketMetricsService().calculate("600519.SH", bars)

    assert result.observation_count == 6
    assert result.returns["5d"] == pytest.approx(0.30)
    assert result.moving_averages["5d"] == pytest.approx(11.5)
    assert result.max_drawdown == pytest.approx(9.0 / 11.0 - 1.0)
    assert result.annualized_volatility is not None


def test_returns_none_when_history_is_insufficient() -> None:
    result = MarketMetricsService().calculate("510300.SH", make_bars([4.0, 4.1]))
    assert result.returns == {"5d": None, "20d": None, "60d": None}
    assert result.moving_averages["5d"] is None
    assert result.volume_ratio is None
```

- [ ] **Step 2: Verify tests fail because analytics do not exist**

Run: `uv run --project backend pytest backend/tests/analytics/test_market_metrics.py -v`

Expected: import failure for `ai_finance.analytics`.

- [ ] **Step 3: Implement the exact calculations**

`MarketMetrics` fields:

```python
class MarketMetrics(BaseModel):
    symbol: str
    observation_count: int
    start_date: date
    end_date: date
    returns: dict[str, float | None]
    moving_averages: dict[str, float | None]
    annualized_volatility: float | None
    max_drawdown: float | None
    volume_ratio: float | None
```

Calculation rules:

- N-day return requires N+1 closes and equals `last_close / close_before_window - 1`.
- N-day moving average requires N closes and uses the final N closes.
- Annualized volatility requires at least three closes and equals sample standard deviation of daily returns times `sqrt(252)`.
- Maximum drawdown is the minimum of `close / cumulative_max_close - 1` over the complete supplied window.
- Volume ratio requires 25 observations and equals mean volume of the latest 5 days divided by mean volume of the preceding 20 days; return `None` when the preceding mean is zero.

- [ ] **Step 4: Verify metrics**

Run: `uv run --project backend pytest backend/tests/analytics -v`

Expected: all metric tests pass.

- [ ] **Step 5: Commit analytics**

```powershell
git add backend/src/ai_finance/analytics backend/tests/analytics
git commit -m "feat: calculate deterministic market metrics"
```

### Task 4: Create the SQLite business schema and repositories

**Files:**
- Create: `backend/src/ai_finance/records/database.py`
- Create: `backend/src/ai_finance/records/models.py`
- Create: `backend/src/ai_finance/records/repositories.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260710_0001_initial.py`
- Create: `backend/tests/records/test_migrations.py`
- Create: `backend/tests/records/test_repositories.py`
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: `Database`, `AnalysisRepository`, `WatchlistRepository`, and `CompletedAnalysisRecord`.
- Produces: persistent runs, events, tool records, structured results, and watchlist rows.

- [ ] **Step 1: Write failing migration and repository tests**

Tests must create a temporary SQLite URL, run `alembic upgrade head`, and assert these tables:

```text
analysis_run
analysis_event
tool_call_record
analysis_result
watchlist_item
alembic_version
```

Repository tests must prove:

- A created run starts as `RUNNING`.
- Event sequences increment per run beginning at 1.
- Listing events after sequence N returns only later events in order.
- A tool record returns its generated evidence ID.
- Completing a run stores the validated result and status `COMPLETE` atomically.
- Watchlist insertion is idempotent by canonical symbol.

- [ ] **Step 2: Verify persistence tests fail**

Run: `uv run --project backend pytest backend/tests/records -v`

Expected: imports or migration configuration are missing.

- [ ] **Step 3: Implement the SQLAlchemy schema**

Use UUID strings for public identifiers and UTC-aware timestamps. Define these required columns:

```text
analysis_run: id, thread_id, user_query, symbol, status, model_name,
              prompt_version, started_at, finished_at, data_cutoff,
              error_code, error_message
analysis_event: id, run_id, sequence, event_type, message, payload_json,
                terminal, created_at; unique(run_id, sequence)
tool_call_record: id, run_id, tool_name, arguments_json, result_json,
                  provider, market_time, retrieved_at, duration_ms,
                  success, error_code
analysis_result: id, run_id unique, market_view, horizon, confidence,
                 summary, supporting_evidence_json, opposing_evidence_json,
                 risks_json, invalidation_conditions_json, full_result_json,
                 created_at
watchlist_item: symbol primary key, display_name, security_type, note, created_at
```

Define this records-layer DTO so persistence does not depend on the AI module created in Task 6:

```python
class CompletedAnalysisRecord(BaseModel):
    market_view: str
    horizon: str
    confidence: float
    summary: str
    supporting_evidence: list[dict[str, str]]
    opposing_evidence: list[dict[str, str]]
    risks: list[str]
    invalidation_conditions: list[str]
    full_result: dict[str, object]
    data_cutoff: datetime
```

Configure SQLite with `PRAGMA foreign_keys=ON` and a five-second busy timeout. Repositories must own transaction boundaries and return Pydantic read models rather than ORM instances.

- [ ] **Step 4: Implement the migration and repositories**

The initial Alembic migration must create the same columns, foreign keys, unique constraints, and indexes as the ORM metadata. Add indexes on run status/start time, tool run ID, event run ID/sequence, and result run ID.

Repository signatures:

```python
create_run(user_query: str, symbol: str, model_name: str,
           prompt_version: str, thread_id: str) -> AnalysisRunRecord
append_event(run_id: str, event_type: str, message: str,
             payload: dict[str, object] | None, terminal: bool) -> AnalysisEventRecord
list_events(run_id: str, after_sequence: int) -> list[AnalysisEventRecord]
record_tool_call(record: NewToolCallRecord) -> ToolCallRecord
list_tool_calls(run_id: str) -> list[ToolCallRecord]
complete_run(run_id: str, result: CompletedAnalysisRecord) -> AnalysisRunRecord
fail_run(run_id: str, error_code: str, error_message: str) -> AnalysisRunRecord
get_run(run_id: str) -> AnalysisRunDetail
list_runs(limit: int, offset: int) -> list[AnalysisRunSummary]
```

- [ ] **Step 5: Verify migrations and repositories**

Run:

```powershell
uv run --project backend pytest backend/tests/records -v
uv run --project backend alembic -c backend/alembic.ini upgrade head
```

Expected: repository tests pass and `data/app.db` is created with the current revision.

- [ ] **Step 6: Commit persistence**

```powershell
git add backend/src/ai_finance/records backend/alembic.ini backend/alembic backend/tests/records data/.gitkeep
git commit -m "feat: persist research runs and watchlist"
```

### Task 5: Expose market and watchlist APIs

**Files:**
- Create: `backend/src/ai_finance/api/container.py`
- Create: `backend/src/ai_finance/api/errors.py`
- Create: `backend/src/ai_finance/api/routes/market.py`
- Create: `backend/src/ai_finance/api/routes/watchlist.py`
- Modify: `backend/src/ai_finance/api/app.py`
- Create: `backend/tests/api/test_market_api.py`
- Create: `backend/tests/api/test_watchlist_api.py`

**Interfaces:**
- Consumes: market and repository interfaces from Tasks 2 through 4.
- Produces: profile, snapshot, daily-bars, and watchlist endpoints from the design.

- [ ] **Step 1: Write failing API tests with injected providers**

Create an `AppContainer` with a fixed in-test provider and a temporary database. Assert:

```text
GET /api/market/600519/profile        -> canonical profile
GET /api/market/510300/snapshot       -> ETF snapshot
GET /api/market/600519/daily-bars?trading_days=60 -> ascending bars
GET /api/market/abc/snapshot          -> 422 INVALID_SYMBOL
GET /api/market/700000/snapshot       -> 422 INVALID_SYMBOL
POST /api/watchlist                   -> 201
POST same symbol again                -> 200 and one row
DELETE /api/watchlist/600519.SH        -> 204
```

- [ ] **Step 2: Verify route tests fail**

Run: `uv run --project backend pytest backend/tests/api/test_market_api.py backend/tests/api/test_watchlist_api.py -v`

Expected: route modules or endpoints are missing.

- [ ] **Step 3: Implement dependency injection and problem details**

`AppContainer` owns settings, market service, metrics service, database, analysis repository, and watchlist repository. `create_app` accepts an optional container for tests and stores it at `app.state.container`.

Every application error response must have this shape:

```json
{
  "type": "about:blank",
  "title": "Invalid security symbol",
  "status": 422,
  "code": "INVALID_SYMBOL",
  "detail": "Unsupported symbol: abc"
}
```

- [ ] **Step 4: Implement market and watchlist routes**

Wrap AKShare calls with these bounded thread operations:

```python
profile = await asyncio.wait_for(
    asyncio.to_thread(market_service.get_security_profile, symbol), timeout=20.0
)
snapshot = await asyncio.wait_for(
    asyncio.to_thread(market_service.get_market_snapshot, symbol), timeout=20.0
)
bars = await asyncio.wait_for(
    asyncio.to_thread(market_service.get_daily_bars, symbol, trading_days), timeout=20.0
)
```

Use `asyncio.to_thread` for synchronous SQLAlchemy work. Validate `trading_days` from 5 through 500. Never return raw provider DataFrames.

- [ ] **Step 5: Verify API behavior**

Run: `uv run --project backend pytest backend/tests/api/test_market_api.py backend/tests/api/test_watchlist_api.py -v`

Expected: all API tests pass.

- [ ] **Step 6: Commit APIs**

```powershell
git add backend/src/ai_finance/api backend/tests/api
git commit -m "feat: expose market and watchlist APIs"
```

### Task 6: Build the DeepSeek LangChain research agent

**Files:**
- Create: `backend/src/ai_finance/ai/schemas.py`
- Create: `backend/src/ai_finance/ai/model_gateway.py`
- Create: `backend/src/ai_finance/ai/prompt.py`
- Create: `backend/src/ai_finance/ai/tools.py`
- Create: `backend/src/ai_finance/ai/runner.py`
- Create: `backend/tests/ai/test_schemas.py`
- Create: `backend/tests/ai/test_tools.py`
- Create: `backend/tests/ai/test_runner.py`
- Create: `backend/tests/live/test_deepseek_smoke.py`

**Interfaces:**
- Consumes: settings, market service, metrics service, and tool-call repository.
- Produces: `ResearchAnalysis`, `ResearchToolFactory`, and `LangChainResearchRunner.run`.

- [ ] **Step 1: Write failing schema, tool, and runner tests**

Schema tests must reject confidence outside 0 through 1, an empty horizon, evidence without an ID, and non-UTC timestamps. Tool tests must prove a result includes its persisted evidence ID and that an identical tool call cannot run twice in one research run. Runner tests inject a fake compiled agent whose `ainvoke` returns a `ResearchAnalysis` under `structured_response` and assert the stable thread ID and recursion limit of 8.

- [ ] **Step 2: Verify AI tests fail**

Run: `uv run --project backend pytest backend/tests/ai -v`

Expected: AI modules do not exist.

- [ ] **Step 3: Implement structured output**

Use these enums and fields:

```python
class AnalysisStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class MarketView(StrEnum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    UNCERTAIN = "UNCERTAIN"


class EvidenceItem(BaseModel):
    evidence_id: str
    statement: str


class ResearchAnalysis(BaseModel):
    status: AnalysisStatus
    symbol: str
    security_name: str
    market_view: MarketView
    horizon: str = Field(min_length=2, max_length=32)
    confidence: float = Field(ge=0, le=1)
    summary: str
    supporting_evidence: list[EvidenceItem]
    opposing_evidence: list[EvidenceItem]
    risks: list[str]
    invalidation_conditions: list[str]
    data_cutoff: datetime
    generated_at: datetime
    model_name: str
    prompt_version: str
```

Validators must require UTC-aware timestamps and `UNCERTAIN` when status is not `COMPLETE`.

- [ ] **Step 4: Implement the model gateway and prompt**

`ModelGateway.create(model_name: str) -> ChatOpenAI` must raise `ModelNotConfiguredError` when the key is absent and configure:

```python
ChatOpenAI(
    model=model_name,
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    timeout=60.0,
    max_retries=1,
    temperature=0.1,
)
```

Prompt version `research-v1` must require successful `get_market_snapshot` and `calculate_market_metrics` calls before returning `COMPLETE`, real tool evidence, both supporting and opposing cases, observable invalidation conditions, explicit horizon, no invented price, and no executable trading order.

- [ ] **Step 5: Implement the four recorded tools**

Create async LangChain tools named exactly:

```python
get_security_profile(symbol: str) -> dict[str, object]
get_market_snapshot(symbol: str) -> dict[str, object]
get_price_history(symbol: str, trading_days: int = 120) -> dict[str, object]
calculate_market_metrics(symbol: str, trading_days: int = 120) -> dict[str, object]
```

Each tool must call the application service through `asyncio.to_thread`, persist arguments/result/duration/provider timestamps, and return a JSON-serializable object containing `evidence_id`. A per-run canonical JSON key prevents an identical tool name and argument object from executing twice.

- [ ] **Step 6: Implement the LangChain runner**

The production runner must:

- Open `AsyncSqliteSaver` using `data/checkpoints.db`.
- Call `setup()` before use.
- Build `create_agent` with the DeepSeek model, four tools, system prompt, checkpointer, and `ToolStrategy(ResearchAnalysis, handle_errors=structured_error_handler)`.
- Implement `structured_error_handler` as a per-run closure: return `"Return exactly one valid research result using only tool evidence."` on the first validation error and re-raise the second error, limiting format repair to one attempt.
- Invoke with `configurable.thread_id` and `recursion_limit=8`.
- Return `result["structured_response"]`.
- Never persist model reasoning content.

- [ ] **Step 7: Add an explicit live smoke test**

Mark the test `live` and skip unless `DEEPSEEK_API_KEY` exists. Define a test-only `get_test_evidence` tool that returns a fixed evidence ID and a synthetic price statement, ask DeepSeek to analyze only that evidence, and assert that the tool was called and the returned `ResearchAnalysis` is valid. Normal `pytest` excludes the marker by default.

- [ ] **Step 8: Verify AI components**

Run:

```powershell
uv run --project backend pytest backend/tests/ai -v
uv run --project backend ruff check backend/src/ai_finance/ai backend/tests/ai
```

Expected: all non-live AI tests pass without API charges.

- [ ] **Step 9: Commit the research agent**

```powershell
git add backend/src/ai_finance/ai backend/tests/ai backend/tests/live
git commit -m "feat: add DeepSeek LangChain research agent"
```

### Task 7: Orchestrate research runs and stream persistent progress

**Files:**
- Create: `backend/src/ai_finance/research/service.py`
- Create: `backend/src/ai_finance/research/validator.py`
- Create: `backend/src/ai_finance/research/sse.py`
- Create: `backend/src/ai_finance/api/routes/research.py`
- Modify: `backend/src/ai_finance/api/container.py`
- Modify: `backend/src/ai_finance/api/app.py`
- Create: `backend/tests/research/test_research_service.py`
- Create: `backend/tests/api/test_research_api.py`

**Interfaces:**
- Consumes: runner, tools, and repositories.
- Produces: create, execute, list, detail, and event-stream research APIs.

- [ ] **Step 1: Write failing service and endpoint tests**

Use a fake runner returning valid structured output and assert the event order:

```text
RUN_CREATED
AGENT_STARTED
AGENT_COMPLETED
RUN_COMPLETED terminal=true
```

Also assert:

- Evidence IDs must belong to successful tool records for the same run.
- A run without successful snapshot and metrics evidence becomes `INSUFFICIENT_DATA` and `UNCERTAIN`.
- Runner exceptions create `RUN_FAILED` and preserve a concise error code.
- `POST /api/research/runs` returns 202 with run ID and event URL.
- SSE honors `Last-Event-ID`, emits ordered event IDs, and closes on a terminal event.
- List and detail endpoints restore completed results.

- [ ] **Step 2: Verify research tests fail**

Run: `uv run --project backend pytest backend/tests/research backend/tests/api/test_research_api.py -v`

Expected: research modules and routes are missing.

- [ ] **Step 3: Implement evidence validation**

`EvidenceValidator` must load successful tool records for the run, require successful `get_market_snapshot` and `calculate_market_metrics` records, verify every evidence ID belongs to the run, and set `data_cutoff` to the latest market timestamp among cited records. It must return a new validated model rather than mutating the model object. `AnalysisRecordMapper` converts the validated `ResearchAnalysis` into the `CompletedAnalysisRecord` defined in Task 4 before repository persistence.

- [ ] **Step 4: Implement run execution**

`ResearchService.start` creates the run and first event. `ResearchService.execute` appends progress events, creates per-run tools, calls the runner, validates evidence, persists completion, and converts known model/provider exceptions to stable error codes. The API schedules `execute` with `asyncio.create_task` in the single local process. An application-scoped `TaskRegistry` retains each task until completion and removes it in a done callback so background research cannot be garbage-collected.

- [ ] **Step 5: Implement database-polled SSE**

The SSE generator polls `analysis_event` every 250 milliseconds for sequences greater than the client cursor and formats:

```text
id: 3
event: AGENT_COMPLETED
data: {"message":"AI analysis completed","payload":{}}

```

It exits after a terminal event or client disconnect. Progress remains recoverable after a page refresh because events are persisted.

- [ ] **Step 6: Verify research orchestration**

Run: `uv run --project backend pytest backend/tests/research backend/tests/api/test_research_api.py -v`

Expected: all service and SSE tests pass.

- [ ] **Step 7: Commit research APIs**

```powershell
git add backend/src/ai_finance/research backend/src/ai_finance/api backend/tests/research backend/tests/api/test_research_api.py
git commit -m "feat: orchestrate and stream research runs"
```

### Task 8: Create the Vue application shell and configuration status

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router.ts`
- Create: `frontend/src/styles/base.css`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/stores/system.ts`
- Create: `frontend/src/layouts/AppLayout.vue`
- Create: `frontend/src/views/ResearchView.vue`
- Create: `frontend/src/views/WatchlistView.vue`
- Create: `frontend/src/views/HistoryView.vue`
- Create: `frontend/src/views/SettingsView.vue`
- Create: `frontend/tests/system.spec.ts`

**Interfaces:**
- Consumes: health and config endpoints.
- Produces: routed Vue shell and connection-status store.

- [ ] **Step 1: Scaffold package configuration**

Use this `package.json`, run `npm install` inside `frontend`, and commit the generated lock file:

```json
{
  "name": "ai-finance-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "axios": "^1.11.0",
    "echarts": "^6.0.0",
    "element-plus": "^2.10.0",
    "pinia": "^3.0.0",
    "vue": "^3.5.0",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.55.0",
    "@types/node": "^24.0.0",
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^26.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0",
    "vitest": "^3.2.0",
    "vue-tsc": "^3.0.0"
  }
}
```

- [ ] **Step 2: Write the failing system-store test**

```typescript
import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '../src/api/client'
import { useSystemStore } from '../src/stores/system'

beforeEach(() => {
  setActivePinia(createPinia())
})

it('loads non-secret backend configuration status', async () => {
  vi.spyOn(api, 'getConfigStatus').mockResolvedValue({
    model_configured: true,
    default_model: 'deepseek-v4-flash',
    deep_model: 'deepseek-v4-pro',
    market_provider: 'akshare',
  })

  const store = useSystemStore()
  await store.load()

  expect(store.modelConfigured).toBe(true)
  expect(store.defaultModel).toBe('deepseek-v4-flash')
})
```

- [ ] **Step 3: Verify the frontend test fails**

Run: `npm test -- --run` from `frontend`.

Expected: imports for the store or client are missing.

- [ ] **Step 4: Implement the shell**

The layout must have a fixed-width navigation rail with Research, Watchlist, History, and Settings routes; a compact top status strip; and a responsive content area. At this task boundary, the first three views contain only their route heading and a stable page container; later tasks replace their contents. It must not use a landing page, nested cards, gradient decoration, or oversized headings.

The Axios client uses `/api` as its base URL. Vite proxies `/api` to `http://127.0.0.1:8000`. The settings view displays boolean connection status and model/provider names but never renders an API key input or secret.

- [ ] **Step 5: Verify the shell**

Run:

```powershell
Set-Location frontend
npm test -- --run
npm run build
```

Expected: Vitest passes and Vite produces `dist` without TypeScript errors.

- [ ] **Step 6: Commit frontend foundation**

```powershell
git add frontend
git commit -m "feat: add Vue application shell"
```

### Task 9: Implement the research workspace

**Files:**
- Create: `frontend/src/stores/research.ts`
- Modify: `frontend/src/views/ResearchView.vue`
- Create: `frontend/src/components/research/ResearchForm.vue`
- Create: `frontend/src/components/research/ResearchProgress.vue`
- Create: `frontend/src/components/research/PriceChart.vue`
- Create: `frontend/src/components/research/MetricsStrip.vue`
- Create: `frontend/src/components/research/AnalysisResult.vue`
- Create: `frontend/tests/research-store.spec.ts`
- Create: `frontend/tests/research-view.spec.ts`

**Interfaces:**
- Consumes: market and research endpoints plus SSE.
- Produces: end-to-end symbol research interaction.

- [ ] **Step 1: Write failing store and view tests**

Tests must prove:

- Submitting `600519` creates a run and opens its event stream.
- Terminal completion loads run detail and chart data.
- An `INSUFFICIENT_DATA` result shows no bullish or bearish action styling.
- Long Chinese evidence wraps without changing control widths.
- Submitting while a run is active is disabled.
- Closing the view closes `EventSource`.

- [ ] **Step 2: Verify research UI tests fail**

Run: `npm test -- --run tests/research-store.spec.ts tests/research-view.spec.ts` from `frontend`.

Expected: research store and components are missing.

- [ ] **Step 3: Implement the research state machine**

Use these client states:

```text
IDLE -> CREATING -> RUNNING -> COMPLETE
                         \-> INSUFFICIENT_DATA
                         \-> FAILED
```

The store owns the active run ID, progress events, result, snapshot, bars, metrics, and error. It must close the previous stream before opening another and reload final detail after a terminal event.

- [ ] **Step 4: Implement the work-focused research layout**

The main grid uses a stable two-column desktop layout and one column below 900 pixels. The left column contains symbol/question controls and an unframed ECharts price-volume plot. The right column contains compact metrics, market view, confidence, horizon, evidence tables, risks, invalidation conditions, source, and data cutoff. Buttons use Element Plus icons where available and include tooltips for unfamiliar icons.

- [ ] **Step 5: Verify the workspace**

Run:

```powershell
Set-Location frontend
npm test -- --run
npm run build
```

Expected: all frontend tests pass and production build succeeds.

- [ ] **Step 6: Commit research UI**

```powershell
git add frontend/src frontend/tests
git commit -m "feat: add AI research workspace"
```

### Task 10: Add watchlist, history, local scripts, and end-to-end verification

**Files:**
- Create: `frontend/src/stores/watchlist.ts`
- Create: `frontend/src/stores/history.ts`
- Modify: `frontend/src/views/WatchlistView.vue`
- Modify: `frontend/src/views/HistoryView.vue`
- Create: `frontend/src/components/history/HistoryTable.vue`
- Create: `frontend/tests/watchlist.spec.ts`
- Create: `frontend/tests/history.spec.ts`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/research.spec.ts`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/e2e_app.py`
- Create: `scripts/dev.ps1`
- Create: `scripts/check.ps1`
- Create: `README.md`
- Modify: `backend/tests/live/test_deepseek_smoke.py`

**Interfaces:**
- Consumes: all Milestone 1 APIs.
- Produces: persisted watchlist/history UI, one-command development startup, full verification command, and operator documentation.

- [ ] **Step 1: Write failing watchlist and history tests**

Assert add/remove watchlist behavior, idempotent symbols, history pagination, status/view filters, and restoring a selected analysis result after refresh.

- [ ] **Step 2: Verify tests fail**

Run: `npm test -- --run tests/watchlist.spec.ts tests/history.spec.ts` from `frontend`.

Expected: stores and views are missing.

- [ ] **Step 3: Implement compact watchlist and history views**

Watchlist rows show canonical symbol, name, type, latest returned price/time, note, analyze command, and remove icon. History rows show time, symbol, status, market view, confidence, horizon, and model; selecting a row renders the complete saved result without making a new model call.

- [ ] **Step 4: Add PowerShell operations**

`scripts/dev.ps1` must:

1. Verify `uv`, `npm`, `.env`, and `DEEPSEEK_API_KEY` availability.
2. Run Alembic upgrade.
3. Start `uv run --project backend uvicorn ai_finance.api.app:app --host 127.0.0.1 --port 8000` in a hidden child process.
4. Start `npm run dev -- --host 127.0.0.1` in `frontend` in the current terminal.
5. Stop the backend child process when the frontend exits.

`scripts/check.ps1` must run Ruff, all non-live pytest tests, Vitest, Vue build, and Playwright in that order and exit nonzero on the first failure.

- [ ] **Step 5: Write Playwright tests before final browser behavior**

The end-to-end test uses `backend/tests/e2e_app.py`, a dedicated test-only API with recorded provider and model responses. Configure Playwright `webServer` entries to start that API and the Vite app automatically. Cover research completion, insufficient data, history restoration, watchlist persistence, and 1440x900 plus 390x844 viewports. Add screenshot assertions and verify the ECharts canvas has nonblank pixels. Run `npx playwright install chromium` once before the first Playwright run.

- [ ] **Step 6: Complete README setup and operations**

Document exact commands:

```powershell
Copy-Item .env.example .env
uv venv --python D:\Pathon\python.exe
uv sync --all-packages --all-extras
Set-Location frontend
npm install
Set-Location ..
.\scripts\dev.ps1
```

Also document AKShare's public-source limitations, DeepSeek API cost, where databases live, how to back them up, how to run the explicit live smoke test, and that Milestone 1 has no brokerage or order execution.

- [ ] **Step 7: Run complete verification**

Run: `.\scripts\check.ps1`

Expected: Ruff, pytest, Vitest, Vue build, and Playwright all succeed with no warnings that indicate runtime failures.

- [ ] **Step 8: Run the explicit real-service smoke checks**

With `.env` configured, run:

```powershell
uv run --project backend pytest backend/tests/live/test_deepseek_smoke.py -m live -v
uv run --project backend python -c "from ai_finance.market.akshare_provider import AkshareMarketDataProvider; print(AkshareMarketDataProvider().get_market_snapshot('600519.SH').model_dump_json())"
```

Expected: DeepSeek returns a validated schema and AKShare returns a real snapshot with provider and retrieval timestamps. If the market is closed, the snapshot may contain the latest available price and must be labeled with retrieval-time timestamp origin.

- [ ] **Step 9: Start and visually inspect the application**

Run `.\scripts\dev.ps1`, open the local Vue URL in the in-app browser, and verify Research, Watchlist, History, and Settings at desktop and mobile widths. Confirm no overlap, clipped Chinese text, blank chart canvas, stale-data mislabeling, or secret display.

- [ ] **Step 10: Commit the complete Milestone 1 application**

```powershell
git add frontend scripts README.md backend/tests/live
git commit -m "feat: complete local AI finance research foundation"
```

## Plan Completion Check

Before declaring Milestone 1 complete:

- Every requirement in the approved design maps to a task above.
- `git status --short` contains no unexpected generated files.
- `data/app.db`, `data/checkpoints.db`, `.env`, and API keys are untracked.
- No backend route, LangChain tool, or frontend command can create an order.
- Runtime providers are AKShare and DeepSeek only; fixtures are restricted to tests.
- The application can be restarted and still restore watchlist and analysis history.
- The user receives the local URL and exact verification result.
