from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from ai_finance.market.symbols import normalize_symbol
from ai_finance.records.database import Database
from ai_finance.records.models import (
    AnalysisEventRecord,
    AnalysisEventRow,
    AnalysisResultRecord,
    AnalysisResultRow,
    AnalysisRunDetail,
    AnalysisRunRecord,
    AnalysisRunRow,
    AnalysisRunSummary,
    CompletedAnalysisRecord,
    NewToolCallRecord,
    ToolCallRecord,
    ToolCallRecordRow,
    WatchlistItemRecord,
    WatchlistItemRow,
    utc_now,
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_utc(value: datetime | None) -> datetime | None:
    return _as_utc(value) if value is not None else None


def _run_record(row: AnalysisRunRow) -> AnalysisRunRecord:
    return AnalysisRunRecord(
        id=row.id,
        thread_id=row.thread_id,
        user_query=row.user_query,
        symbol=row.symbol,
        status=row.status,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        started_at=_as_utc(row.started_at),
        finished_at=_optional_utc(row.finished_at),
        data_cutoff=_optional_utc(row.data_cutoff),
        error_code=row.error_code,
        error_message=row.error_message,
    )


def _event_record(row: AnalysisEventRow) -> AnalysisEventRecord:
    return AnalysisEventRecord(
        id=row.id,
        run_id=row.run_id,
        sequence=row.sequence,
        event_type=row.event_type,
        message=row.message,
        payload=row.payload_json,
        terminal=row.terminal,
        created_at=_as_utc(row.created_at),
    )


def _tool_record(row: ToolCallRecordRow) -> ToolCallRecord:
    return ToolCallRecord(
        id=row.id,
        run_id=row.run_id,
        tool_name=row.tool_name,
        arguments=row.arguments_json,
        result=row.result_json,
        provider=row.provider,
        market_time=_optional_utc(row.market_time),
        retrieved_at=_as_utc(row.retrieved_at),
        duration_ms=row.duration_ms,
        success=row.success,
        error_code=row.error_code,
    )


def _result_record(row: AnalysisResultRow) -> AnalysisResultRecord:
    return AnalysisResultRecord(
        id=row.id,
        run_id=row.run_id,
        market_view=row.market_view,
        horizon=row.horizon,
        confidence=row.confidence,
        summary=row.summary,
        supporting_evidence=row.supporting_evidence_json,
        opposing_evidence=row.opposing_evidence_json,
        risks=row.risks_json,
        invalidation_conditions=row.invalidation_conditions_json,
        full_result=row.full_result_json,
        created_at=_as_utc(row.created_at),
    )


def _watchlist_record(row: WatchlistItemRow) -> WatchlistItemRecord:
    return WatchlistItemRecord(
        symbol=row.symbol,
        display_name=row.display_name,
        security_type=row.security_type,
        note=row.note,
        created_at=_as_utc(row.created_at),
    )


def _require_run(session: Session, run_id: str) -> AnalysisRunRow:
    row = session.get(AnalysisRunRow, run_id)
    if row is None:
        raise LookupError(f"Analysis run not found: {run_id}")
    return row


class AnalysisRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_run(
        self,
        user_query: str,
        symbol: str,
        model_name: str,
        prompt_version: str,
        thread_id: str,
    ) -> AnalysisRunRecord:
        row = AnalysisRunRow(
            thread_id=thread_id,
            user_query=user_query,
            symbol=normalize_symbol(symbol),
            status="RUNNING",
            model_name=model_name,
            prompt_version=prompt_version,
            started_at=utc_now(),
        )
        with self._database.session() as session, session.begin():
            session.add(row)
            session.flush()
            record = _run_record(row)
        return record

    def append_event(
        self,
        run_id: str,
        event_type: str,
        message: str,
        payload: dict[str, object] | None,
        terminal: bool,
    ) -> AnalysisEventRecord:
        with self._database.session() as session, session.begin():
            _require_run(session, run_id)
            last_sequence = session.scalar(
                select(func.max(AnalysisEventRow.sequence)).where(AnalysisEventRow.run_id == run_id)
            )
            row = AnalysisEventRow(
                run_id=run_id,
                sequence=(last_sequence or 0) + 1,
                event_type=event_type,
                message=message,
                payload_json=payload,
                terminal=terminal,
                created_at=utc_now(),
            )
            session.add(row)
            session.flush()
            record = _event_record(row)
        return record

    def list_events(self, run_id: str, after_sequence: int) -> list[AnalysisEventRecord]:
        with self._database.session() as session, session.begin():
            rows = session.scalars(
                select(AnalysisEventRow)
                .where(
                    AnalysisEventRow.run_id == run_id,
                    AnalysisEventRow.sequence > after_sequence,
                )
                .order_by(AnalysisEventRow.sequence)
            ).all()
            records = [_event_record(row) for row in rows]
        return records

    def record_tool_call(self, record: NewToolCallRecord) -> ToolCallRecord:
        row = ToolCallRecordRow(
            run_id=record.run_id,
            tool_name=record.tool_name,
            arguments_json=record.arguments,
            result_json=record.result,
            provider=record.provider,
            market_time=_optional_utc(record.market_time),
            retrieved_at=_as_utc(record.retrieved_at),
            duration_ms=record.duration_ms,
            success=record.success,
            error_code=record.error_code,
        )
        with self._database.session() as session, session.begin():
            _require_run(session, record.run_id)
            session.add(row)
            session.flush()
            saved_record = _tool_record(row)
        return saved_record

    def list_tool_calls(self, run_id: str) -> list[ToolCallRecord]:
        with self._database.session() as session, session.begin():
            rows = session.scalars(
                select(ToolCallRecordRow)
                .where(ToolCallRecordRow.run_id == run_id)
                .order_by(ToolCallRecordRow.retrieved_at, ToolCallRecordRow.id)
            ).all()
            records = [_tool_record(row) for row in rows]
        return records

    def complete_run(self, run_id: str, result: CompletedAnalysisRecord) -> AnalysisRunRecord:
        now = utc_now()
        with self._database.session() as session, session.begin():
            run = _require_run(session, run_id)
            session.add(
                AnalysisResultRow(
                    run_id=run_id,
                    market_view=result.market_view,
                    horizon=result.horizon,
                    confidence=result.confidence,
                    summary=result.summary,
                    supporting_evidence_json=result.supporting_evidence,
                    opposing_evidence_json=result.opposing_evidence,
                    risks_json=result.risks,
                    invalidation_conditions_json=result.invalidation_conditions,
                    full_result_json=result.full_result,
                    created_at=now,
                )
            )
            run.status = "COMPLETE"
            run.finished_at = now
            run.data_cutoff = _as_utc(result.data_cutoff)
            run.error_code = None
            run.error_message = None
            session.flush()
            record = _run_record(run)
        return record

    def fail_run(self, run_id: str, error_code: str, error_message: str) -> AnalysisRunRecord:
        with self._database.session() as session, session.begin():
            run = _require_run(session, run_id)
            run.status = "FAILED"
            run.finished_at = utc_now()
            run.error_code = error_code
            run.error_message = error_message
            session.flush()
            record = _run_record(run)
        return record

    def get_run(self, run_id: str) -> AnalysisRunDetail:
        with self._database.session() as session, session.begin():
            run = _require_run(session, run_id)
            result = session.scalar(
                select(AnalysisResultRow).where(AnalysisResultRow.run_id == run_id)
            )
            events = session.scalars(
                select(AnalysisEventRow)
                .where(AnalysisEventRow.run_id == run_id)
                .order_by(AnalysisEventRow.sequence)
            ).all()
            tool_calls = session.scalars(
                select(ToolCallRecordRow)
                .where(ToolCallRecordRow.run_id == run_id)
                .order_by(ToolCallRecordRow.retrieved_at, ToolCallRecordRow.id)
            ).all()
            detail = AnalysisRunDetail(
                **_run_record(run).model_dump(),
                result=_result_record(result) if result is not None else None,
                events=[_event_record(event) for event in events],
                tool_calls=[_tool_record(tool_call) for tool_call in tool_calls],
            )
        return detail

    def list_runs(self, limit: int, offset: int) -> list[AnalysisRunSummary]:
        with self._database.session() as session, session.begin():
            rows = session.execute(
                select(AnalysisRunRow, AnalysisResultRow)
                .outerjoin(AnalysisResultRow, AnalysisResultRow.run_id == AnalysisRunRow.id)
                .order_by(AnalysisRunRow.started_at.desc(), AnalysisRunRow.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            records = [
                AnalysisRunSummary(
                    **_run_record(run).model_dump(),
                    market_view=result.market_view if result is not None else None,
                    horizon=result.horizon if result is not None else None,
                    confidence=result.confidence if result is not None else None,
                    summary=result.summary if result is not None else None,
                )
                for run, result in rows
            ]
        return records


class WatchlistRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(
        self,
        symbol: str,
        display_name: str,
        security_type: str,
        note: str | None = None,
    ) -> WatchlistItemRecord:
        canonical_symbol = normalize_symbol(symbol)
        with self._database.session() as session, session.begin():
            session.execute(
                sqlite_insert(WatchlistItemRow)
                .values(
                    symbol=canonical_symbol,
                    display_name=display_name,
                    security_type=security_type,
                    note=note,
                    created_at=utc_now(),
                )
                .on_conflict_do_nothing(index_elements=[WatchlistItemRow.symbol])
            )
            row = session.get(WatchlistItemRow, canonical_symbol)
            if row is None:
                raise RuntimeError(f"Failed to persist watchlist item: {canonical_symbol}")
            record = _watchlist_record(row)
        return record

    def get(self, symbol: str) -> WatchlistItemRecord | None:
        canonical_symbol = normalize_symbol(symbol)
        with self._database.session() as session, session.begin():
            row = session.get(WatchlistItemRow, canonical_symbol)
            record = _watchlist_record(row) if row is not None else None
        return record

    def list_items(self) -> list[WatchlistItemRecord]:
        with self._database.session() as session, session.begin():
            rows = session.scalars(select(WatchlistItemRow).order_by(WatchlistItemRow.symbol)).all()
            records = [_watchlist_record(row) for row in rows]
        return records

    def remove(self, symbol: str) -> bool:
        canonical_symbol = normalize_symbol(symbol)
        with self._database.session() as session, session.begin():
            row = session.get(WatchlistItemRow, canonical_symbol)
            if row is None:
                return False
            session.delete(row)
        return True
