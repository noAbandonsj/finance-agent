import pytest
from langchain.agents import create_agent
from langchain_core.tools import tool

from ai_finance.ai.model_gateway import ModelGateway
from ai_finance.settings import Settings


@pytest.mark.live
@pytest.mark.asyncio
async def test_deepseek_calls_tool_and_returns_markdown_research() -> None:
    settings = Settings()
    if not settings.model_configured:
        pytest.skip("DEEPSEEK_API_KEY is not configured")

    tool_called = False

    @tool
    def get_test_evidence() -> dict[str, str]:
        """Return the only evidence allowed in this synthetic research task."""
        nonlocal tool_called
        tool_called = True
        return {
            "evidence_id": "test-evidence-1",
            "statement": "The synthetic instrument price is 100 at 2026-07-11T00:00:00Z.",
        }

    agent = create_agent(
        model=ModelGateway(settings).create(settings.deepseek_default_model),
        tools=[get_test_evidence],
        system_prompt=(
            "Call get_test_evidence exactly once. Analyze only that synthetic evidence. "
            "Then return a concise Markdown report that cites test-evidence-1."
        ),
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Analyze the synthetic instrument."}]},
        config={"recursion_limit": 8},
    )

    assert tool_called is True
    assert result["messages"][-1].content
    assert "test-evidence-1" in result["messages"][-1].content
