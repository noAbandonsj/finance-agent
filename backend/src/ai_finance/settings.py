from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-finance-backend"
    host: str = "127.0.0.1"
    port: int = 8000
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-v4-flash"
    deepseek_deep_model: str = "deepseek-v4-pro"
    database_url: str = "sqlite:///data/app.db"
    checkpoint_path: Path = Path("data/checkpoints.db")
    market_provider: str = "akshare"

    @property
    def model_configured(self) -> bool:
        return self.deepseek_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
