import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ai_finance.market.symbols import InvalidSymbolError
from ai_finance.shared.errors import ProviderUnavailableError, SecurityNotFoundError


def problem_response(status: int, title: str, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidSymbolError)
    async def invalid_symbol_handler(_request: Request, exc: InvalidSymbolError) -> JSONResponse:
        return problem_response(422, "Invalid security symbol", "INVALID_SYMBOL", str(exc))

    @app.exception_handler(SecurityNotFoundError)
    async def security_not_found_handler(
        _request: Request, exc: SecurityNotFoundError
    ) -> JSONResponse:
        return problem_response(404, "Security not found", exc.code, str(exc))

    @app.exception_handler(ProviderUnavailableError)
    async def provider_unavailable_handler(
        _request: Request, exc: ProviderUnavailableError
    ) -> JSONResponse:
        return problem_response(503, "Market provider unavailable", exc.code, str(exc))

    @app.exception_handler(asyncio.TimeoutError)
    async def provider_timeout_handler(
        _request: Request, _exc: asyncio.TimeoutError
    ) -> JSONResponse:
        return problem_response(
            504,
            "Market provider timeout",
            "PROVIDER_TIMEOUT",
            "Market data request exceeded 20 seconds",
        )

    @app.exception_handler(LookupError)
    async def record_not_found_handler(_request: Request, exc: LookupError) -> JSONResponse:
        return problem_response(404, "Record not found", "RECORD_NOT_FOUND", str(exc))
