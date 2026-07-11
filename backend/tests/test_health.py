from fastapi.testclient import TestClient

from ai_finance.api.app import create_app
from ai_finance.settings import Settings


def test_config_status_never_returns_api_key() -> None:
    settings = Settings(deepseek_api_key="secret-value", _env_file=None)
    response = TestClient(create_app(settings)).get("/api/config/status")

    assert response.status_code == 200
    assert response.json() == {
        "model_configured": True,
        "default_model": "deepseek-v4-flash",
        "deep_model": "deepseek-v4-pro",
        "market_provider": "akshare",
    }
    assert "secret-value" not in response.text


def test_health_is_local_service_ready() -> None:
    response = TestClient(create_app(Settings(_env_file=None))).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-finance-backend"}


def test_empty_api_key_is_not_reported_as_configured() -> None:
    settings = Settings(deepseek_api_key="   ", _env_file=None)

    response = TestClient(create_app(settings)).get("/api/config/status")

    assert response.json()["model_configured"] is False
