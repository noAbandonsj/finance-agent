import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable

from ai_finance.records.repositories import AnalysisRepository


async def stream_research_events(
    repository: AnalysisRepository,
    run_id: str,
    after_sequence: int,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_interval: float = 0.25,
) -> AsyncIterator[str]:
    cursor = after_sequence
    while True:
        if await is_disconnected():
            return
        events = await asyncio.to_thread(repository.list_events, run_id, cursor)
        for event in events:
            payload = json.dumps(
                {"message": event.message, "payload": event.payload or {}},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {payload}\n\n"
            cursor = event.sequence
            if event.terminal:
                return
        if not events:
            detail = await asyncio.to_thread(repository.get_run, run_id)
            if detail.status != "RUNNING":
                return
        await asyncio.sleep(poll_interval)
