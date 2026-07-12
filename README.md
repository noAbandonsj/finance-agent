# AI Finance Desk

AI Finance Desk is a local personal financial research application. A LangChain agent backed by
DeepSeek autonomously chooses AKShare market tools and writes a Markdown research report. Every
tool call, result, data timestamp, and failure is retained for audit. The Vue interface provides
research, watchlist, history, and runtime status views.

The current milestone is read-only. It cannot create brokerage orders or move real funds.

## Requirements

- Windows PowerShell
- Python 3.13.7 at `D:\Pathon\python.exe`
- uv
- Node.js 24 or newer and npm
- A paid or credited DeepSeek API key for AI research

## Setup

```powershell
Copy-Item .env.example .env
uv venv --python D:\Pathon\python.exe
uv sync --all-packages --all-extras
Set-Location frontend
npm install
Set-Location ..
```

Edit `.env` and set `DEEPSEEK_API_KEY`. Do not commit that file.

Initialize and start both applications:

```powershell
.\scripts\dev.ps1
```

Open `http://127.0.0.1:5173`. The API listens only on `http://127.0.0.1:8000`.

## Verification

Install the Playwright browser once:

```powershell
Set-Location frontend
npx playwright install chromium
Set-Location ..
```

Run all offline checks:

```powershell
.\scripts\check.ps1
```

Run explicit real-service smoke checks only when `.env` contains a funded DeepSeek key:

```powershell
uv run --project backend pytest backend/tests/live/test_deepseek_smoke.py -m live -v
uv run --project backend python -c "from ai_finance.market.akshare_provider import AkshareMarketDataProvider; print(AkshareMarketDataProvider().get_market_snapshot('600519.SH').model_dump_json())"
```

## Local Data

- `data/app.db`: watchlist, research runs, events, tool evidence, and final results.
- `data/checkpoints.db`: LangGraph conversation checkpoints.

Stop the application before backing up these files. Copy both files together so research records
and agent checkpoints remain aligned.

AKShare aggregates public market sources. Availability, schemas, and timestamps can change, so the
application labels provider and retrieval time and never treats public snapshots as exchange-grade
execution data. DeepSeek calls incur API charges according to the selected model and current
provider pricing.

## Scope

Supported now: A-share stocks and exchange-traded funds, latest snapshots, daily price history,
deterministic metrics, AI Markdown research, tool audit, watchlist, and history restoration.

Not implemented: portfolio accounting, paper orders, broker connectivity, executable orders,
automatic trading, authentication, or remote deployment.

Future trading tools must remain behind deterministic risk checks and an approval or policy gate.
Natural-language model output must never bypass structured order parameters and execution audit.
