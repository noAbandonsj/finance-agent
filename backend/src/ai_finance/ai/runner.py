from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_finance.ai.model_gateway import ModelGateway
from ai_finance.ai.prompt import RESEARCH_SYSTEM_PROMPT


class EmptyAgentReportError(RuntimeError):
    code = "EMPTY_AGENT_REPORT"


class CompiledResearchAgent(Protocol):
    async def ainvoke(self, input_value: dict[str, object], config: dict[str, object]) -> Any: ...


class LangChainResearchRunner:
    def __init__(self, compiled_agent: CompiledResearchAgent) -> None:
        self._compiled_agent = compiled_agent

    async def run(self, user_query: str, thread_id: str) -> str:
        result = await self._compiled_agent.ainvoke(
            {"messages": [{"role": "user", "content": user_query}]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 8},
        )
        report = _extract_final_report(result)
        if not report:
            raise EmptyAgentReportError("The agent returned an empty research report")
        return report

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        model_gateway: ModelGateway,
        model_name: str,
        tools: Sequence[BaseTool],
        checkpoint_path: Path,
    ) -> AsyncIterator["LangChainResearchRunner"]:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
            await checkpointer.setup()
            compiled_agent = create_agent(
                model=model_gateway.create(model_name),
                tools=list(tools),
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                checkpointer=checkpointer,
            )
            yield cls(compiled_agent)


def _extract_final_report(result: object) -> str:
    if not isinstance(result, dict):
        return ""
    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""
    message = messages[-1]
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        else:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(part.strip() for part in parts if part.strip()).strip()
