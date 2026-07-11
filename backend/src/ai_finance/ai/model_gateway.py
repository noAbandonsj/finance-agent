from langchain_openai import ChatOpenAI

from ai_finance.settings import Settings


class ModelNotConfiguredError(RuntimeError):
    code = "MODEL_NOT_CONFIGURED"


class ModelGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, model_name: str) -> ChatOpenAI:
        if self._settings.deepseek_api_key is None:
            raise ModelNotConfiguredError("DEEPSEEK_API_KEY is not configured")

        return ChatOpenAI(
            model=model_name,
            api_key=self._settings.deepseek_api_key,
            base_url=self._settings.deepseek_base_url,
            timeout=60.0,
            max_retries=1,
            temperature=0.1,
        )
