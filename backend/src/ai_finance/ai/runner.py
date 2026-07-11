from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ai_finance.ai.model_gateway import ModelGateway
from ai_finance.ai.prompt import RESEARCH_SYSTEM_PROMPT
from ai_finance.ai.schemas import ResearchAnalysis


class CompiledResearchAgent(Protocol):
    async def ainvoke(self, input_value: dict[str, object], config: dict[str, object]) -> Any: ...


class LangChainResearchRunner:
    def __init__(self, compiled_agent: CompiledResearchAgent) -> None:
        self._compiled_agent = compiled_agent

    async def run(self, user_query: str, thread_id: str) -> ResearchAnalysis:
        result = await self._compiled_agent.ainvoke(
            {"messages": [{"role": "user", "content": user_query}]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 8},
        )
        return ResearchAnalysis.model_validate(result["structured_response"])

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
            repair_count = 0

            def structured_error_handler(error: Exception) -> str:
                nonlocal repair_count
                repair_count += 1
                if repair_count > 1:
                    raise error
                return "Return exactly one valid research result using only tool evidence."

            compiled_agent = create_agent(
                model=model_gateway.create(model_name),
                tools=list(tools),
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                checkpointer=checkpointer,
                response_format=ToolStrategy(
                    ResearchAnalysis,
                    handle_errors=structured_error_handler,
                ),
            )
            yield cls(compiled_agent)
