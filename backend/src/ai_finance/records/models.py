from datetime import datetime, timezone
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class AnalysisRunRow(Base):
    __tablename__ = "analysis_run"
    __table_args__ = (Index("ix_analysis_run_status_started_at", "status", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_cutoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)


class AnalysisEventRow(Base):
    __tablename__ = "analysis_event"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_analysis_event_run_id_sequence"),
        Index("ix_analysis_event_run_id_sequence", "run_id", "sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_run.id", ondelete="CASCADE", name="fk_analysis_event_run_id"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    terminal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ToolCallRecordRow(Base):
    __tablename__ = "tool_call_record"
    __table_args__ = (Index("ix_tool_call_record_run_id", "run_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_run.id", ondelete="CASCADE", name="fk_tool_call_record_run_id"),
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    provider: Mapped[str | None] = mapped_column(String(64))
    market_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class AnalysisResultRow(Base):
    __tablename__ = "analysis_result"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_analysis_result_run_id"),
        Index("ix_analysis_result_run_id", "run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_run.id", ondelete="CASCADE", name="fk_analysis_result_run_id"),
        nullable=False,
    )
    market_view: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_json: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    opposing_evidence_json: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    risks_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    invalidation_conditions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    full_result_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WatchlistItemRow(Base):
    __tablename__ = "watchlist_item"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    security_type: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True)


class CompletedAnalysisRecord(FrozenRecord):
    market_view: str
    horizon: str
    confidence: float
    summary: str
    supporting_evidence: list[dict[str, str]]
    opposing_evidence: list[dict[str, str]]
    risks: list[str]
    invalidation_conditions: list[str]
    full_result: dict[str, object]
    data_cutoff: AwareDatetime


class AnalysisRunRecord(FrozenRecord):
    id: str
    thread_id: str
    user_query: str
    symbol: str
    status: str
    model_name: str
    prompt_version: str
    started_at: datetime
    finished_at: datetime | None
    data_cutoff: datetime | None
    error_code: str | None
    error_message: str | None


class AnalysisEventRecord(FrozenRecord):
    id: str
    run_id: str
    sequence: int
    event_type: str
    message: str
    payload: dict[str, object] | None
    terminal: bool
    created_at: datetime


class NewToolCallRecord(FrozenRecord):
    run_id: str
    tool_name: str
    arguments: dict[str, object]
    result: dict[str, object] | None
    provider: str | None
    market_time: AwareDatetime | None
    retrieved_at: AwareDatetime
    duration_ms: int
    success: bool
    error_code: str | None = None


class ToolCallRecord(NewToolCallRecord):
    id: str


class AnalysisResultRecord(FrozenRecord):
    id: str
    run_id: str
    market_view: str
    horizon: str
    confidence: float
    summary: str
    supporting_evidence: list[dict[str, str]]
    opposing_evidence: list[dict[str, str]]
    risks: list[str]
    invalidation_conditions: list[str]
    full_result: dict[str, object]
    created_at: datetime


class AnalysisRunSummary(AnalysisRunRecord):
    market_view: str | None = None
    horizon: str | None = None
    confidence: float | None = None
    summary: str | None = None


class AnalysisRunDetail(AnalysisRunRecord):
    result: AnalysisResultRecord | None = None
    events: list[AnalysisEventRecord] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)


class WatchlistItemRecord(FrozenRecord):
    symbol: str
    display_name: str
    security_type: str
    note: str | None
    created_at: datetime
