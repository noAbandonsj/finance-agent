from fastapi import APIRouter, Request

from ai_finance.settings import Settings

router = APIRouter()


@router.get("/health")
def get_health(request: Request) -> dict[str, str]:
    settings: Settings = request.app.state.settings
    return {"status": "ok", "service": settings.app_name}


@router.get("/config/status")
def get_config_status(request: Request) -> dict[str, bool | str]:
    settings: Settings = request.app.state.settings
    return {
        "model_configured": settings.model_configured,
        "default_model": settings.deepseek_default_model,
        "deep_model": settings.deepseek_deep_model,
        "market_provider": settings.market_provider,
    }
