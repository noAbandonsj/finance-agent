from ai_finance.ai.schemas import AnalysisStatus, MarketView, ResearchAnalysis
from ai_finance.records.models import CompletedAnalysisRecord
from ai_finance.records.repositories import AnalysisRepository


class EvidenceValidationError(ValueError):
    code = "INVALID_EVIDENCE"


class EvidenceValidator:
    REQUIRED_TOOLS = {"get_market_snapshot", "calculate_market_metrics"}

    def __init__(self, repository: AnalysisRepository) -> None:
        self._repository = repository

    def validate(self, run_id: str, analysis: ResearchAnalysis) -> ResearchAnalysis:
        records = [record for record in self._repository.list_tool_calls(run_id) if record.success]
        records_by_id = {record.id: record for record in records}
        evidence_ids = {
            item.evidence_id for item in analysis.supporting_evidence + analysis.opposing_evidence
        }
        unknown_ids = evidence_ids - records_by_id.keys()
        if unknown_ids:
            unknown = ", ".join(sorted(unknown_ids))
            raise EvidenceValidationError(f"Evidence does not belong to this run: {unknown}")

        cited_market_times = [
            records_by_id[evidence_id].market_time
            for evidence_id in evidence_ids
            if records_by_id[evidence_id].market_time is not None
        ]
        data_cutoff = max(cited_market_times, default=analysis.generated_at)
        successful_tools = {record.tool_name for record in records}

        if not self.REQUIRED_TOOLS.issubset(successful_tools):
            return analysis.model_copy(
                update={
                    "status": AnalysisStatus.INSUFFICIENT_DATA,
                    "market_view": MarketView.UNCERTAIN,
                    "confidence": 0.0,
                    "data_cutoff": data_cutoff,
                }
            )

        return analysis.model_copy(update={"data_cutoff": data_cutoff})


class AnalysisRecordMapper:
    @staticmethod
    def to_record(analysis: ResearchAnalysis) -> CompletedAnalysisRecord:
        return CompletedAnalysisRecord(
            market_view=analysis.market_view.value,
            horizon=analysis.horizon,
            confidence=analysis.confidence,
            summary=analysis.summary,
            supporting_evidence=[item.model_dump() for item in analysis.supporting_evidence],
            opposing_evidence=[item.model_dump() for item in analysis.opposing_evidence],
            risks=analysis.risks,
            invalidation_conditions=analysis.invalidation_conditions,
            full_result=analysis.model_dump(mode="json"),
            data_cutoff=analysis.data_cutoff,
        )
