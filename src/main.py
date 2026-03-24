# src/main.py
from src.shared.config.settings import settings


def run_api():
    import uvicorn
    from src.shared.config.logging_config import setup_logging

    setup_logging(settings.LOG_LEVEL.value)

    uvicorn.run(
        "src.services.api_gateway.app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        # reload=settings.is_development,
        reload_dirs=["src"],

        # reload_excludes=[
        #     "**/*.pyc",
        #     "**/*.pyo",
        #     "**/__pycache__/**",
        #     "data/**",
        #     "logs/**",
        #     "temp/**",
        #     ".pytest_cache/**"
        # ],
        workers=settings.API_WORKERS,
        # log_level=settings.LOG_LEVEL.value,
        log_config=None
    )
