import asyncio

from fastapi import APIRouter, Query, Request

from ai_finance.api.container import AppContainer
from ai_finance.market.models import DailyBar, MarketSnapshot, SecurityProfile


router = APIRouter(prefix="/market", tags=["market"])


def _container(request: Request) -> AppContainer:
    return request.app.state.container


@router.get("/{symbol}/profile", response_model=SecurityProfile)
async def get_profile(symbol: str, request: Request) -> SecurityProfile:
    service = _container(request).market_service
    return await asyncio.wait_for(
        asyncio.to_thread(service.get_security_profile, symbol),
        timeout=20.0,
    )


@router.get("/{symbol}/snapshot", response_model=MarketSnapshot)
async def get_snapshot(symbol: str, request: Request) -> MarketSnapshot:
    service = _container(request).market_service
    return await asyncio.wait_for(
        asyncio.to_thread(service.get_market_snapshot, symbol),
        timeout=20.0,
    )


@router.get("/{symbol}/daily-bars", response_model=list[DailyBar])
async def get_daily_bars(
    symbol: str,
    request: Request,
    trading_days: int = Query(default=60, ge=5, le=500),
) -> list[DailyBar]:
    service = _container(request).market_service
    return await asyncio.wait_for(
        asyncio.to_thread(service.get_daily_bars, symbol, trading_days),
        timeout=20.0,
    )
