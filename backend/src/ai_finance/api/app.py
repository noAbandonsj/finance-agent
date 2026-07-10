from fastapi import FastAPI

from ai_finance.api.routes.health import router as health_router
from ai_finance.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings if settings is not None else get_settings()
    application = FastAPI(title=app_settings.app_name)
    application.state.settings = app_settings
    application.include_router(health_router, prefix="/api")
    return application


app = create_app()
