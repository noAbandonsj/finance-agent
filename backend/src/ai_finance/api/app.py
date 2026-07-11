from fastapi import FastAPI

from ai_finance.api.container import AppContainer
from ai_finance.api.errors import register_error_handlers
from ai_finance.api.routes.health import router as health_router
from ai_finance.api.routes.market import router as market_router
from ai_finance.api.routes.research import router as research_router
from ai_finance.api.routes.watchlist import router as watchlist_router
from ai_finance.settings import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    container: AppContainer | None = None,
) -> FastAPI:
    app_settings = settings if settings is not None else get_settings()
    application = FastAPI(title=app_settings.app_name)
    application.state.settings = app_settings
    application.state.container = container or AppContainer.create(app_settings)
    register_error_handlers(application)
    application.include_router(health_router, prefix="/api")
    application.include_router(market_router, prefix="/api")
    application.include_router(research_router, prefix="/api")
    application.include_router(watchlist_router, prefix="/api")
    return application


app = create_app()
