from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ai_finance.ai.schemas import (
    AnalysisStatus,
    EvidenceItem,
    MarketView,
    ResearchAnalysis,
)


def valid_analysis(**overrides) -> ResearchAnalysis:
    values = {
        "status": AnalysisStatus.COMPLETE,
        "symbol": "600519.SH",
        "security_name": "Kweichow Moutai",
        "market_view": MarketView.NEUTRAL,
        "horizon": "20 trading days",
        "confidence": 0.65,
        "summary": "Balanced evidence.",
        "supporting_evidence": [EvidenceItem(evidence_id="e-1", statement="support")],
        "opposing_evidence": [EvidenceItem(evidence_id="e-2", statement="oppose")],
        "risks": ["valuation"],
        "invalidation_conditions": ["price trend reverses"],
        "data_cutoff": datetime(2026, 7, 11, tzinfo=timezone.utc),
        "generated_at": datetime(2026, 7, 11, 1, tzinfo=timezone.utc),
        "model_name": "deepseek-v4-pro",
        "prompt_version": "research-v1",
    }
    values.update(overrides)
    return ResearchAnalysis.model_validate(values)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_rejects_confidence_outside_unit_interval(confidence: float) -> None:
    with pytest.raises(ValidationError):
        valid_analysis(confidence=confidence)


def test_rejects_empty_horizon_and_evidence_id() -> None:
    with pytest.raises(ValidationError):
        valid_analysis(horizon="")
    with pytest.raises(ValidationError):
        EvidenceItem(evidence_id="", statement="missing source")


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 7, 11),
        datetime(2026, 7, 11, tzinfo=timezone(timedelta(hours=8))),
    ],
)
def test_rejects_non_utc_timestamps(timestamp: datetime) -> None:
    with pytest.raises(ValidationError):
        valid_analysis(data_cutoff=timestamp)


def test_non_complete_status_requires_uncertain_view() -> None:
    with pytest.raises(ValidationError):
        valid_analysis(status=AnalysisStatus.INSUFFICIENT_DATA, market_view=MarketView.BULLISH)

    result = valid_analysis(
        status=AnalysisStatus.INSUFFICIENT_DATA,
        market_view=MarketView.UNCERTAIN,
    )
    assert result.market_view is MarketView.UNCERTAIN
