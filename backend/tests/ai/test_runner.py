from types import SimpleNamespace

import pytest

from ai_finance.ai.model_gateway import ModelGateway, ModelNotConfiguredError
from ai_finance.ai.runner import EmptyAgentReportError, LangChainResearchRunner
from ai_finance.settings import Settings


class FakeCompiledAgent:
    def __init__(self, content: object) -> None:
        self.content = content
        self.inputs = []
        self.configs = []

    async def ainvoke(self, input_value, config):
        self.inputs.append(input_value)
        self.configs.append(config)
        return {"messages": [SimpleNamespace(content=self.content)]}


@pytest.mark.asyncio
async def test_runner_returns_text_with_stable_thread_and_bounded_recursion() -> None:
    compiled_agent = FakeCompiledAgent("# Report\n\nBalanced.")
    runner = LangChainResearchRunner(compiled_agent)

    result = await runner.run("analyze this", thread_id="research-run-1")

    assert result == "# Report\n\nBalanced."
    assert compiled_agent.inputs == [{"messages": [{"role": "user", "content": "analyze this"}]}]
    assert compiled_agent.configs == [
        {"configurable": {"thread_id": "research-run-1"}, "recursion_limit": 8}
    ]


@pytest.mark.asyncio
async def test_runner_combines_text_content_blocks() -> None:
    runner = LangChainResearchRunner(
        FakeCompiledAgent(
            [
                {"type": "text", "text": "# Report"},
                {"type": "reasoning", "text": "hidden"},
                {"type": "output_text", "text": "Conclusion."},
            ]
        )
    )

    assert await runner.run("analyze", "thread-1") == "# Report\nConclusion."


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["", "   ", [], [{"type": "reasoning", "text": "hidden"}]])
async def test_runner_rejects_empty_final_report(content: object) -> None:
    runner = LangChainResearchRunner(FakeCompiledAgent(content))

    with pytest.raises(EmptyAgentReportError):
        await runner.run("analyze", "thread-1")


@pytest.mark.asyncio
async def test_agent_creation_does_not_force_response_format_or_tool_choice(
    monkeypatch, tmp_path
) -> None:
    captured: dict[str, object] = {}
    compiled_agent = FakeCompiledAgent("Report")

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return compiled_agent

    class FakeGateway:
        def create(self, model_name: str) -> object:
            return object()

    monkeypatch.setattr("ai_finance.ai.runner.create_agent", fake_create_agent)

    async with LangChainResearchRunner.create(
        model_gateway=FakeGateway(),
        model_name="test-model",
        tools=[],
        checkpoint_path=tmp_path / "checkpoints.db",
    ):
        pass

    assert "response_format" not in captured
    assert "tool_choice" not in captured
    assert captured["tools"] == []


def test_model_gateway_requires_real_api_key() -> None:
    gateway = ModelGateway(Settings(deepseek_api_key=None, _env_file=None))

    with pytest.raises(ModelNotConfiguredError):
        gateway.create("deepseek-v4-flash")


def test_model_gateway_configures_deepseek_chat_client() -> None:
    model = ModelGateway(
        Settings(
            deepseek_api_key="secret", deepseek_base_url="https://example.test", _env_file=None
        )
    ).create("deepseek-v4-flash")

    assert model.model_name == "deepseek-v4-flash"
    assert model.temperature == 0.1
    assert str(model.openai_api_base) == "https://example.test"
    assert model.max_retries == 1
