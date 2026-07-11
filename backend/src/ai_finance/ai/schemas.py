from datetime import datetime, timedelta
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnalysisStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class MarketView(StrEnum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    UNCERTAIN = "UNCERTAIN"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class ResearchAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AnalysisStatus
    symbol: str
    security_name: str
    market_view: MarketView
    horizon: str = Field(min_length=2, max_length=32)
    confidence: float = Field(ge=0, le=1)
    summary: str
    supporting_evidence: list[EvidenceItem]
    opposing_evidence: list[EvidenceItem]
    risks: list[str]
    invalidation_conditions: list[str]
    data_cutoff: datetime
    generated_at: datetime
    model_name: str
    prompt_version: str

    @field_validator("data_cutoff", "generated_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be UTC-aware")
        return value

    @model_validator(mode="after")
    def require_uncertain_for_incomplete_analysis(self) -> Self:
        if (
            self.status is not AnalysisStatus.COMPLETE
            and self.market_view is not MarketView.UNCERTAIN
        ):
            raise ValueError("non-complete analysis must use an UNCERTAIN market view")
        return self
