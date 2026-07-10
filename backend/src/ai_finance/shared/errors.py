from typing import ClassVar


class ProviderUnavailableError(RuntimeError):
    code: ClassVar[str] = "PROVIDER_UNAVAILABLE"

    def __init__(self, detail: str = "Market data provider is unavailable") -> None:
        self.detail = detail
        super().__init__(detail)


class SecurityNotFoundError(LookupError):
    code: ClassVar[str] = "SECURITY_NOT_FOUND"

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Security not found: {symbol}")
