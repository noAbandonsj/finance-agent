from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI, Response, status
from fastapi.responses import StreamingResponse


app = FastAPI()
runs: dict[str, dict[str, object]] = {}
watchlist: dict[str, dict[str, object]] = {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-finance-backend"}


@app.get("/api/config/status")
def config_status() -> dict[str, object]:
    return {
        "model_configured": True,
        "default_model": "deepseek-v4-flash",
        "deep_model": "deepseek-v4-pro",
        "market_provider": "recorded-e2e",
    }


@app.post("/api/research/runs", status_code=status.HTTP_202_ACCEPTED)
def create_run(payload: dict[str, str]) -> dict[str, str]:
    run_id = str(uuid4())
    raw_symbol = payload["symbol"].split(".")[0]
    symbol = f"{raw_symbol}.{'SH' if raw_symbol.startswith(('5', '6', '9')) else 'SZ'}"
    insufficient = raw_symbol == "510300"
    analysis_status = "INSUFFICIENT_DATA" if insufficient else "COMPLETE"
    market_view = "UNCERTAIN" if insufficient else "NEUTRAL"
    analysis = {
        "status": analysis_status,
        "symbol": symbol,
        "security_name": "Recorded Security",
        "market_view": market_view,
        "horizon": "20 trading days",
        "confidence": 0 if insufficient else 0.64,
        "summary": "数据不足，暂不形成方向判断。"
        if insufficient
        else "量价证据相互制衡，当前维持中性判断。",
        "supporting_evidence": []
        if insufficient
        else [{"evidence_id": "snapshot-1", "statement": "最新价格保持稳定。"}],
        "opposing_evidence": []
        if insufficient
        else [{"evidence_id": "metrics-1", "statement": "短期波动仍然存在。"}],
        "risks": ["测试环境中的记录数据不代表实时市场"],
        "invalidation_conditions": ["价格趋势发生显著变化"],
        "data_cutoff": "2026-07-11T00:00:00Z",
        "generated_at": "2026-07-11T00:01:00Z",
        "model_name": "deepseek-v4-pro",
        "prompt_version": "research-v1",
    }
    runs[run_id] = {
        "id": run_id,
        "thread_id": f"thread-{run_id}",
        "user_query": payload["question"],
        "symbol": symbol,
        "status": "COMPLETE",
        "model_name": "deepseek-v4-pro",
        "prompt_version": "research-v1",
        "started_at": "2026-07-11T00:00:00Z",
        "finished_at": "2026-07-11T00:01:00Z",
        "data_cutoff": "2026-07-11T00:00:00Z",
        "error_code": None,
        "error_message": None,
        "result": {"full_result": analysis},
        "events": [],
        "tool_calls": [
            {
                "id": "metrics-1",
                "run_id": run_id,
                "tool_name": "calculate_market_metrics",
                "arguments": {},
                "result": {
                    "symbol": symbol,
                    "observation_count": 60,
                    "start_date": "2026-05-01",
                    "end_date": "2026-07-11",
                    "returns": {"5d": 0.02, "20d": 0.04, "60d": None},
                    "moving_averages": {"5d": 10.2},
                    "annualized_volatility": 0.18,
                    "max_drawdown": -0.08,
                    "volume_ratio": 1.1,
                },
                "provider": "recorded-e2e",
                "market_time": "2026-07-11T00:00:00Z",
                "retrieved_at": "2026-07-11T00:00:01Z",
                "duration_ms": 1,
                "success": True,
                "error_code": None,
            }
        ],
    }
    return {"run_id": run_id, "event_url": f"/api/research/runs/{run_id}/events"}


@app.get("/api/research/runs/{run_id}/events")
def events(run_id: str) -> StreamingResponse:
    def generate():
        yield 'id: 1\nevent: RUN_CREATED\ndata: {"message":"Research run created","payload":{}}\n\n'
        yield 'id: 2\nevent: AGENT_STARTED\ndata: {"message":"AI research started","payload":{}}\n\n'
        yield 'id: 3\nevent: AGENT_COMPLETED\ndata: {"message":"AI analysis completed","payload":{}}\n\n'
        yield 'id: 4\nevent: RUN_COMPLETED\ndata: {"message":"Research run completed","payload":{}}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/research/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    return runs[run_id]


@app.get("/api/research/runs")
def list_runs() -> list[dict[str, object]]:
    return [
        {
            "id": run["id"],
            "symbol": run["symbol"],
            "status": run["status"],
            "model_name": run["model_name"],
            "started_at": run["started_at"],
            "market_view": run["result"]["full_result"]["market_view"],
            "confidence": run["result"]["full_result"]["confidence"],
            "horizon": run["result"]["full_result"]["horizon"],
            "summary": run["result"]["full_result"]["summary"],
        }
        for run in reversed(list(runs.values()))
    ]


@app.get("/api/market/{symbol}/snapshot")
def snapshot(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "name": "Recorded Security",
        "security_type": "ETF" if symbol.startswith("5") else "STOCK",
        "last": 10.5,
        "previous_close": 10.4,
        "open": 10.4,
        "high": 10.6,
        "low": 10.3,
        "change_percent": 0.96,
        "volume": 100000,
        "amount": 1050000,
        "market_time": "2026-07-11T00:00:00Z",
        "timestamp_origin": "recorded",
        "provider": "recorded-e2e",
        "retrieved_at": "2026-07-11T00:00:01Z",
    }


@app.get("/api/market/{symbol}/daily-bars")
def daily_bars(symbol: str) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "trading_date": (date(2026, 5, 1) + timedelta(days=index)).isoformat(),
            "open": 9.5 + index * 0.02,
            "high": 9.7 + index * 0.02,
            "low": 9.4 + index * 0.02,
            "close": 9.6 + index * 0.02,
            "volume": 1000 + index * 20,
            "amount": 10000 + index * 200,
            "provider": "recorded-e2e",
        }
        for index in range(60)
    ]


@app.get("/api/watchlist")
def get_watchlist() -> list[dict[str, object]]:
    return list(watchlist.values())


@app.post("/api/watchlist")
def add_watchlist(payload: dict[str, str | None], response: Response) -> dict[str, object]:
    raw_symbol = str(payload["symbol"]).split(".")[0]
    symbol = f"{raw_symbol}.{'SH' if raw_symbol.startswith(('5', '6', '9')) else 'SZ'}"
    created = symbol not in watchlist
    watchlist.setdefault(
        symbol,
        {
            "symbol": symbol,
            "display_name": "Recorded Security",
            "security_type": "ETF" if symbol.startswith("5") else "STOCK",
            "note": payload.get("note"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    response.status_code = 201 if created else 200
    return watchlist[symbol]


@app.delete("/api/watchlist/{symbol}", status_code=204)
def delete_watchlist(symbol: str) -> Response:
    watchlist.pop(symbol, None)
    return Response(status_code=204)
