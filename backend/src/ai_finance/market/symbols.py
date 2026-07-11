import re


_SYMBOL_PATTERN = re.compile(
    r"^(?:(SH|SZ|BJ)[.-]?)?(\d{6})(?:[.-]?(SH|SZ|BJ))?$",
    re.IGNORECASE,
)


class InvalidSymbolError(ValueError):
    """Raised when a security identifier cannot be normalized."""


def normalize_symbol(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidSymbolError(f"Unsupported symbol: {value}")

    compact = re.sub(r"\s+", "", value).upper()
    match = _SYMBOL_PATTERN.fullmatch(compact)
    if match is None:
        raise InvalidSymbolError(f"Unsupported symbol: {value}")

    prefix, code, suffix = match.groups()
    exchange = _infer_exchange(code)
    explicit_exchange = prefix or suffix
    if (prefix and suffix and prefix != suffix) or (
        explicit_exchange and explicit_exchange != exchange
    ):
        raise InvalidSymbolError(f"Unsupported symbol: {value}")

    return f"{code}.{exchange}"


def _infer_exchange(code: str) -> str:
    if code.startswith("92") or code[0] in {"4", "8"}:
        return "BJ"
    if code[0] in {"5", "6", "9"}:
        return "SH"
    if code[0] in {"0", "1", "2", "3"}:
        return "SZ"
    raise InvalidSymbolError(f"Unsupported symbol: {code}")
