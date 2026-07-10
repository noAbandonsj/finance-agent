# AI Finance Research Foundation Design

**Date:** 2026-07-10  
**Status:** Approved  
**Audience:** Personal, single-user Windows deployment

## 1. Purpose

Build the first working slice of a personal AI-native financial assistant for A-share stocks and exchange-traded funds. The assistant uses real market data and a real DeepSeek API key, decides which approved research tools to call, calculates quantitative metrics in Python, and returns a structured, traceable market analysis.

This milestone establishes boundaries that support later portfolio accounting, multi-agent research, autonomous paper trading, and broker-backed live trading without replacing the initial application architecture.

## 2. Product Principles

1. AI leads the research process and selects relevant approved tools.
2. Providers supply facts; Python supplies deterministic calculations; the model supplies synthesis and judgment.
3. Missing data remains missing. The model must not invent prices, financial values, news, or tool results.
4. Every conclusion records its market-data source, data cutoff, model, prompt version, and tool evidence.
5. Trading is introduced in stages. The model never bypasses portfolio accounting, deterministic risk policy, or broker execution services.
6. Local usability takes priority over concurrency, multi-user access, distributed infrastructure, and cloud deployment.

## 3. Scope

### 3.1 Milestone 1: Research Mode

Milestone 1 includes:

- A-share stock and exchange-traded fund symbol input.
- Real latest market snapshots and historical daily bars from AKShare.
- Deterministic calculation of returns, moving averages, volatility, maximum drawdown, and volume changes.
- A LangChain `create_agent` research agent backed by DeepSeek.
- A restricted set of read-only market and analytics tools.
- Structured analysis with market view, horizon, confidence, evidence, risks, and invalidation conditions.
- A Vue research workspace with charting, progress streaming, watchlist, and analysis history.
- SQLite persistence for business records and separate SQLite checkpoint persistence for agent conversations.

### 3.2 Explicit Non-Goals for Milestone 1

Milestone 1 does not include:

- Brokerage connectivity or real order submission.
- Paper-account cash, positions, orders, trades, or ledger accounting.
- Autonomous scheduling or unattended analysis.
- Company filings, announcements, financial statements, or news tools.
- Minute, tick, Level-2, or continuously collected market data.
- Multi-agent orchestration.
- User accounts, authentication, remote access, or cloud deployment.
- Docker, Redis, PostgreSQL, Kafka, Celery, or microservices.

These capabilities belong to later milestones and must use the boundaries defined in Section 11.

## 4. Technology Decisions

### 4.1 Backend

- Python 3.11.
- FastAPI for local HTTP and Server-Sent Events APIs.
- LangChain `create_agent` for the initial tool-calling agent loop.
- `langchain-openai` `ChatOpenAI` configured with the DeepSeek OpenAI-compatible base URL.
- `deepseek-v4-flash` as the default model; `deepseek-v4-pro` as a configurable deeper-analysis model.
- Pydantic v2 for all API, tool, provider, and structured model-output contracts.
- SQLAlchemy 2.x and Alembic for business persistence and migrations.
- SQLite for local business data.
- LangGraph SQLite Checkpointer for LangChain short-term memory and resumable state.
- pandas and NumPy for quantitative calculations.
- AKShare as the initial market-data provider.

LangChain remains the application-level agent API. LangGraph is its underlying runtime and a future composition point, not a custom workflow authored in Milestone 1.

### 4.2 Frontend

- Vue 3 with TypeScript and Vite.
- Composition API with `<script setup>`.
- Vue Router for application views.
- Pinia for client state.
- Element Plus for dense application controls and tables.
- ECharts for daily price and volume charts.
- Native `EventSource` or a small SSE client for analysis progress.

### 4.3 Local Operation

- FastAPI and Vue run directly on Windows.
- The backend binds to `127.0.0.1` by default.
- No Docker or locally installed database server is required.
- `DEEPSEEK_API_KEY` is loaded from `.env` or the process environment and is never stored in SQLite.
- Runtime analysis requires a real DeepSeek key and real provider data. Test doubles exist only under test code.

## 5. Architecture

```text
Vue 3 research workspace
        |
        | HTTP + SSE
        v
FastAPI modular monolith
        |
        +-- ResearchApplicationService
        |       |
        |       +-- LangChain ResearchAgent
        |       |       +-- approved read-only tools
        |       |       +-- DeepSeek ModelGateway
        |       |
        |       +-- EvidenceValidator
        |       +-- AnalysisRepository
        |
        +-- MarketApplicationService
                +-- MarketDataProvider
                |       +-- AkshareMarketDataProvider
                |       +-- future QmtMarketDataProvider
                +-- MarketMetricsService

SQLite app.db             SQLite checkpoints.db
business records          agent thread/checkpoint state
```

The backend is a modular monolith. Modules communicate through typed application services and protocols rather than through direct imports of provider or model SDK details.

## 6. Module Responsibilities

### 6.1 Market Module

Responsibilities:

- Normalize input symbols to the canonical `000001.SZ` or `510300.SH` form.
- Distinguish A-share stocks and exchange-traded funds.
- Fetch and normalize security profiles, market snapshots, and daily bars.
- Attach `provider`, `market_time`, and `retrieved_at` to every result.
- Return typed unavailable results instead of fabricated or partially inferred values.

Primary protocol:

```python
class MarketDataProvider(Protocol):
    def get_security_profile(self, symbol: str) -> SecurityProfile: ...
    def get_market_snapshot(self, symbol: str) -> MarketSnapshot: ...
    def get_daily_bars(self, symbol: str, trading_days: int) -> list[DailyBar]: ...
```

AKShare-specific Chinese column names and source response shapes remain inside `AkshareMarketDataProvider`.

### 6.2 Analytics Module

`MarketMetricsService` consumes normalized daily bars and calculates:

- 5-, 20-, and 60-trading-day returns when enough observations exist.
- 5-, 20-, and 60-day simple moving averages.
- Annualized volatility from daily returns.
- Maximum drawdown over the requested window.
- Recent volume ratio against a defined trailing average.

Each metric is nullable and carries an observation count. Insufficient history is not silently extrapolated.

### 6.3 AI Module

`ModelGateway` constructs and configures the DeepSeek-compatible `ChatOpenAI` instance. The rest of the application does not instantiate SDK clients.

The initial `ResearchAgent` uses LangChain `create_agent` with four tools:

- `get_security_profile(symbol)`
- `get_market_snapshot(symbol)`
- `get_price_history(symbol, trading_days)`
- `calculate_market_metrics(symbol, trading_days)`

Tool names, argument schemas, and return schemas are stable application contracts. Tool execution records are persisted independently of LangChain messages.

A run permits at most eight model steps. An identical tool call with identical arguments may not execute twice in the same run. These limits bound accidental loops and API cost without changing the agent's authority to select the research path.

The agent uses an explicit tool-based structured-output strategy with a Pydantic schema so compatibility does not depend on provider-native structured-output detection.

### 6.4 Research Module

`ResearchApplicationService`:

1. Creates an analysis run.
2. Invokes the LangChain agent with a stable thread ID.
3. Streams progress events to the caller.
4. Validates required evidence and structured output.
5. Persists the final analysis or a typed failure.

The agent may choose tools and query horizons, but it may only use the approved tool registry. It cannot access the file system, execute commands, write application data directly, or place trades.

### 6.5 Records Module

The records module owns analysis history and the watchlist. It does not depend on LangChain message storage.

## 7. Request and Data Flow

For a request such as "Analyze 600519.SH over the next 20 trading days":

1. The API validates the request and creates `analysis_run` with status `RUNNING`.
2. The agent determines which approved tools to call.
3. Market tools fetch real AKShare data and normalize it.
4. Analytics tools calculate metrics from normalized bars.
5. Each tool result is saved with its arguments, provider, market time, retrieval time, duration, and success state.
6. The agent synthesizes a structured `ResearchAnalysis` result.
7. Deterministic validation verifies symbol consistency, evidence timestamps, required fields, and value ranges.
8. The result is saved and streamed to the Vue client.
9. If required market evidence is unavailable, the run ends as `INSUFFICIENT_DATA` without a directional market view.

## 8. Structured Analysis Contract

`ResearchAnalysis` contains:

- `status`: `COMPLETE`, `INSUFFICIENT_DATA`, or `FAILED`.
- `symbol` and security name.
- `market_view`: `BULLISH`, `NEUTRAL`, `BEARISH`, or `UNCERTAIN`.
- `horizon`: an explicit trading-day horizon.
- `confidence`: a value from 0 through 1.
- `summary`.
- `supporting_evidence`: factual statements containing the supporting `tool_call_record` ID.
- `opposing_evidence`: factual statements containing the supporting `tool_call_record` ID.
- `risks`.
- `invalidation_conditions` expressed as observable conditions.
- `data_cutoff` and `generated_at`.
- `model_name` and `prompt_version`.

The contract intentionally does not contain an executable order. Future trade proposals are a separate domain object.

## 9. Persistence Design

### 9.1 Business Database: `data/app.db`

Alembic manages these Milestone 1 tables:

#### `analysis_run`

- Run ID and conversation thread ID.
- User query and normalized symbol.
- Status and selected model.
- Prompt version.
- Start, finish, and data-cutoff timestamps.
- Error code and concise error message.

#### `tool_call_record`

- Run ID.
- Tool name.
- Arguments JSON.
- Normalized result JSON.
- Provider and market-data timestamp.
- Retrieval timestamp and duration.
- Success flag and error code.

#### `analysis_result`

- Run ID.
- Market view, horizon, confidence, and summary.
- Supporting evidence, opposing evidence, risks, and invalidation conditions as JSON.
- Full validated result JSON.

#### `analysis_event`

- Run ID and monotonically increasing sequence number.
- Event type, user-facing message, optional payload JSON, and creation time.
- Terminal flag used by the SSE endpoint to stop polling after completion or failure.

#### `watchlist_item`

- Canonical symbol.
- Display name, security type, note, and creation time.

### 9.2 Agent Checkpoints: `data/checkpoints.db`

LangGraph SQLite Checkpointer owns its internal schema. Alembic does not manage this file. Thread IDs link checkpoints to `analysis_run` records without coupling business queries to checkpoint internals.

### 9.3 Future Time-Series Storage

Milestone 1 stores tool evidence associated with analyses and does not continuously collect the market. When minute or long-running daily collection is introduced, normalized time series are written to Parquet and queried with DuckDB. Business state remains in SQLite.

## 10. API and User Interface

### 10.1 API Surface

- `GET /api/health`
- `GET /api/config/status`
- `GET /api/market/{symbol}/profile`
- `GET /api/market/{symbol}/snapshot`
- `GET /api/market/{symbol}/daily-bars`
- `POST /api/research/runs`
- `GET /api/research/runs/{run_id}/events`
- `GET /api/research/runs/{run_id}`
- `GET /api/research/runs`
- `GET /api/watchlist`
- `POST /api/watchlist`
- `DELETE /api/watchlist/{symbol}`

All errors use a consistent problem-details response with a stable application error code.

### 10.2 Vue Views

The application opens directly into the research workspace.

- **Research:** symbol input, question input, progress, daily chart, calculated metrics, structured AI analysis, evidence, risks, invalidation conditions, and data cutoff.
- **Watchlist:** compact table with symbol, name, latest available price/time, note, and research action.
- **History:** filterable analysis runs with status, view, confidence, model, and timestamp; selecting a run restores its full result.
- **Settings:** non-secret configuration status for DeepSeek and AKShare, configured model names, local database locations, and service health.

The UI uses a restrained operational layout. It does not include a landing page, decorative dashboard cards, nested cards, or feature-description copy.

## 11. Long-Term Stable Boundaries

The following protocols and services define the future system shape even though most implementations are deferred:

```text
MarketDataProvider    current and historical prices
DocumentProvider      filings, announcements, financials, and news
AnalysisToolRegistry  market, fundamental, quantitative, and event tools
Broker                account, positions, previews, orders, and cancellations
RiskPolicy            deterministic position and loss limits
PortfolioService      cash, positions, valuation, P&L, and ledger accounting
ResearchAgent         coordinating research agent
SpecialistAgent       market, fundamental, quantitative, event, and risk agents
ExecutionService      proposal validation and broker execution
```

Specialist agents are exposed to the coordinator as tools. When the topology requires parallel branches, fixed review stages, or long-running workflows, the existing LangChain agent is embedded as a node in a LangGraph `StateGraph`.

The model never receives a raw `Broker.submit_order` tool. It calls `request_trade`, which produces a typed `TradeProposal`. `RiskPolicy` and `ExecutionService` determine whether the proposal may become an order in the current operating mode.

## 12. Operating Modes and Roadmap

### Level 1: Research Mode

Milestone 1. Real data and AI research; no account or order execution.

### Level 2: Human-Approved Paper Trading

Add `PaperBroker`, paper account, cash ledger, positions, orders, trades, valuation, and a portfolio page. The agent creates proposals; the user approves, edits, or rejects them.

### Level 3: Autonomous Paper Trading

Add a local scheduler, autonomous research triggers, deterministic risk policy, idempotent order requests, and unattended paper execution. The backend must remain running for scheduled work.

### Level 4: Human-Approved Live Trading

Add `QmtMarketDataProvider` and `QmtBroker` after the user obtains the required broker terminal and permissions. Run shadow mode first, then require approval for every live order.

### Level 5: Constrained Autonomous Live Trading

Allow automatic live execution only within independently configured symbol allowlists, maximum position size, maximum order value, total exposure, daily loss, data freshness, order-rate, and kill-switch limits. The agent cannot edit these limits or change the operating mode.

Before any live programmatic trading, the user must confirm broker access requirements and applicable reporting procedures. Current CSRC and exchange rules apply a report-before-trading framework to programmatically generated or submitted exchange orders.

## 13. Error Handling

- Missing `DEEPSEEK_API_KEY`: the server starts, reports `MODEL_NOT_CONFIGURED`, and rejects research requests without sending a model call.
- AKShare timeout or schema change: retry briefly, record the provider error, and end as `INSUFFICIENT_DATA` when required evidence is missing.
- DeepSeek timeout or rate limit: record the failure and expose a manual retry action; do not retry indefinitely.
- Invalid structured output: perform at most one format-repair attempt, then mark the run `FAILED`.
- Market closed: display the provider's market timestamp and do not label the last observation as live.
- SQLite write contention: keep transactions short and return a typed service-unavailable error if the bounded retry fails.
- Application restart: completed business records remain in `app.db`; agent thread state remains in `checkpoints.db`.

## 14. Testing Strategy

### 14.1 Backend Unit Tests

- Symbol normalization and invalid symbols.
- AKShare response normalization for stocks and exchange-traded funds.
- Metric calculations, insufficient-history behavior, and null values.
- Evidence validation and data-cutoff selection.
- Structured-analysis validation.
- Repository persistence and migrations.

### 14.2 Backend Integration Tests

- Provider contract tests use recorded responses and never depend on the public network during the normal test suite.
- Model contract tests replace DeepSeek HTTP responses with deterministic fixtures.
- A separately marked real-API smoke test runs only when `DEEPSEEK_API_KEY` is configured explicitly.
- API tests cover successful research, insufficient data, model failure, history, and watchlist behavior.

### 14.3 Frontend Tests

- Vitest covers stores, API-state transitions, and core result rendering.
- Playwright covers the research workflow, history restoration, error states, and desktop/mobile layout.
- Browser verification checks that charts render, results do not overlap, and long Chinese text remains within containers.

Test doubles are restricted to test code. The runtime application contains no fake model or fake market-data provider.

## 15. Milestone 1 Acceptance Criteria

1. A PowerShell command starts the local FastAPI and Vue development processes.
2. The settings view reports whether the DeepSeek key and market provider are configured.
3. A user can enter an A-share stock or exchange-traded fund symbol and retrieve a real AKShare profile, latest snapshot, and daily history.
4. The LangChain agent autonomously selects approved tools and produces a Pydantic-validated research analysis using DeepSeek.
5. The UI displays price history, metrics, market view, horizon, confidence, supporting and opposing evidence, risks, invalidation conditions, sources, and data cutoff.
6. Analysis progress is visible through SSE.
7. Refreshing the browser preserves watchlist entries and completed analysis history.
8. Missing provider data never results in an invented price or directional conclusion.
9. Backend, frontend, and Playwright tests pass.
10. No brokerage function or executable order endpoint exists in Milestone 1.

## 16. Initial Repository Shape

```text
ai-finance-assistant/
├─ backend/
│  ├─ src/ai_finance/
│  │  ├─ api/
│  │  ├─ ai/
│  │  ├─ market/
│  │  ├─ analytics/
│  │  ├─ research/
│  │  ├─ records/
│  │  └─ shared/
│  ├─ tests/
│  ├─ alembic/
│  ├─ alembic.ini
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  ├─ tests/
│  ├─ package.json
│  └─ vite.config.ts
├─ data/
├─ scripts/
├─ docs/
├─ .env.example
└─ README.md
```

The repository begins as one project with two application directories. Backend modules are separated by domain responsibility, not deployed as microservices.

## 17. Sources Informing the Design

- DeepSeek OpenAI-compatible API and current model names: <https://api-docs.deepseek.com/>
- LangChain agent runtime: <https://docs.langchain.com/oss/python/langchain/agents>
- LangChain middleware and future graph composition: <https://docs.langchain.com/oss/python/langchain/middleware/overview>
- LangChain human-in-the-loop middleware: <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>
- LangGraph SQLite Checkpointer: <https://docs.langchain.com/oss/python/integrations/checkpointers/index>
- AKShare A-share data interfaces: <https://akshare.akfamily.xyz/data/stock/stock.html>
- CSRC programmatic trading rules: <https://www.csrc.gov.cn/csrc/c100028/c7480577/content.shtml>
- Shanghai Stock Exchange implementation rules: <https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20250612_10781696.shtml>
- Shenzhen Stock Exchange implementation rules: <https://www.szse.cn/lawrules/rule/trade/current/t20250403_612770.html>
