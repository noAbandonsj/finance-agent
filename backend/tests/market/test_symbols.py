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


def test_normalize_symbol_removes_whitespace() -> None:
    assert normalize_symbol(" 60 0519 . sh ") == "600519.SH"


@pytest.mark.parametrize(
    "raw",
    ["", "abc", "12345", "700000", "600519.HK", "600519.SZ"],
)
def test_rejects_unsupported_symbol(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_symbol(raw)
