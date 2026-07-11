import asyncio

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from ai_finance.api.container import AppContainer
from ai_finance.api.errors import problem_response
from ai_finance.market.symbols import normalize_symbol
from ai_finance.records.models import WatchlistItemRecord


router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistCreate(BaseModel):
    symbol: str
    note: str | None = Field(default=None, max_length=2000)


def _container(request: Request) -> AppContainer:
    return request.app.state.container


@router.get("", response_model=list[WatchlistItemRecord])
async def list_watchlist(request: Request) -> list[WatchlistItemRecord]:
    repository = _container(request).watchlist_repository
    return await asyncio.to_thread(repository.list_items)


@router.post("", response_model=WatchlistItemRecord)
async def add_watchlist_item(
    payload: WatchlistCreate,
    request: Request,
    response: Response,
) -> WatchlistItemRecord:
    container = _container(request)
    symbol = normalize_symbol(payload.symbol)
    existing = await asyncio.to_thread(container.watchlist_repository.get, symbol)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    profile = await asyncio.wait_for(
        asyncio.to_thread(container.market_service.get_security_profile, symbol),
        timeout=20.0,
    )
    item = await asyncio.to_thread(
        container.watchlist_repository.add,
        profile.symbol,
        profile.name,
        profile.security_type.value,
        payload.note,
    )
    response.status_code = status.HTTP_201_CREATED
    return item


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_item(symbol: str, request: Request) -> Response:
    canonical_symbol = normalize_symbol(symbol)
    repository = _container(request).watchlist_repository
    removed = await asyncio.to_thread(repository.remove, canonical_symbol)
    if not removed:
        return problem_response(
            status.HTTP_404_NOT_FOUND,
            "Watchlist item not found",
            "WATCHLIST_ITEM_NOT_FOUND",
            f"Watchlist item not found: {canonical_symbol}",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
