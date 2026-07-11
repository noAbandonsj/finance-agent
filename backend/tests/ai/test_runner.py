from datetime import datetime, timezone

import pytest

from ai_finance.ai.model_gateway import ModelGateway, ModelNotConfiguredError
from ai_finance.ai.runner import LangChainResearchRunner
from ai_finance.ai.schemas import AnalysisStatus, MarketView, ResearchAnalysis
from ai_finance.settings import Settings


def make_analysis() -> ResearchAnalysis:
    return ResearchAnalysis(
        status=AnalysisStatus.COMPLETE,
        symbol="600519.SH",
        security_name="Kweichow Moutai",
        market_view=MarketView.NEUTRAL,
        horizon="20 trading days",
        confidence=0.6,
        summary="Balanced.",
        supporting_evidence=[],
        opposing_evidence=[],
        risks=[],
        invalidation_conditions=[],
        data_cutoff=datetime(2026, 7, 11, tzinfo=timezone.utc),
        generated_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        model_name="test-model",
        prompt_version="research-v1",
    )


class FakeCompiledAgent:
    def __init__(self, analysis: ResearchAnalysis) -> None:
        self.analysis = analysis
        self.inputs = []
        self.configs = []

    async def ainvoke(self, input_value, config):
        self.inputs.append(input_value)
        self.configs.append(config)
        return {"structured_response": self.analysis}


@pytest.mark.asyncio
async def test_runner_uses_stable_thread_and_bounded_recursion() -> None:
    compiled_agent = FakeCompiledAgent(make_analysis())
    runner = LangChainResearchRunner(compiled_agent)

    result = await runner.run("analyze this", thread_id="research-run-1")

    assert result == make_analysis()
    assert compiled_agent.inputs == [{"messages": [{"role": "user", "content": "analyze this"}]}]
    assert compiled_agent.configs == [
        {"configurable": {"thread_id": "research-run-1"}, "recursion_limit": 8}
    ]


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
