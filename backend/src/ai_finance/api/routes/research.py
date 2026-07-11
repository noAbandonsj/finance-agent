import asyncio

from fastapi import APIRouter, Header, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_finance.api.container import AppContainer
from ai_finance.records.models import AnalysisRunDetail, AnalysisRunSummary
from ai_finance.research.sse import stream_research_events


router = APIRouter(prefix="/research/runs", tags=["research"])


class ResearchRunCreate(BaseModel):
    symbol: str
    question: str = Field(min_length=2, max_length=2000)


class ResearchRunAccepted(BaseModel):
    run_id: str
    event_url: str


def _container(request: Request) -> AppContainer:
    return request.app.state.container


@router.post("", response_model=ResearchRunAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_research_run(payload: ResearchRunCreate, request: Request) -> ResearchRunAccepted:
    container = _container(request)
    run = await container.research_service.start(payload.question, payload.symbol)
    container.task_registry.start(container.research_service.execute(run.id))
    return ResearchRunAccepted(
        run_id=run.id,
        event_url=f"/api/research/runs/{run.id}/events",
    )


@router.get("", response_model=list[AnalysisRunSummary])
async def list_research_runs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AnalysisRunSummary]:
    repository = _container(request).analysis_repository
    return await asyncio.to_thread(repository.list_runs, limit, offset)


@router.get("/{run_id}", response_model=AnalysisRunDetail)
async def get_research_run(run_id: str, request: Request) -> AnalysisRunDetail:
    repository = _container(request).analysis_repository
    return await asyncio.to_thread(repository.get_run, run_id)


@router.get("/{run_id}/events")
async def get_research_events(
    run_id: str,
    request: Request,
    last_event_id: int = Header(default=0, alias="Last-Event-ID", ge=0),
) -> Response:
    repository = _container(request).analysis_repository
    await asyncio.to_thread(repository.get_run, run_id)
    events = stream_research_events(
        repository=repository,
        run_id=run_id,
        after_sequence=last_event_id,
        is_disconnected=request.is_disconnected,
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
