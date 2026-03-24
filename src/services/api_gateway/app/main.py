import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles


from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from src.shared.storage.cache_service import ChatCacheService, VideoCacheService
from src.shared.storage.queue_service import QueueService
from src.shared.storage.storage_service import StorageService
from src.services.query_services.app.handlers.query_service import QueryService
from src.services.video_ingestion.app.handlers.video_service import VideoService
from src.services.llm_service.app.mcp_service import MCPService
from src.services.api_gateway.app.routes import (
    home_routes,
    video_routes,
    query_routes,
    health_routes,
)

# Define the absolute path to your data folder
DATA_DIR = "/home/chethan/Desktop/Chethan/aiml_projects/advanced_projects/personal_ai/video_analytics/data"

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage provider based on settings"""
    storage_service = StorageService(settings.STORAGE_PROVIDER)
    queue_service = QueueService(settings.QUEUE_PROVIDER, "video_queue")
    video_cache_service = VideoCacheService(settings.CACHE_PROVIDER)
    chat_cache_service = ChatCacheService(settings.CACHE_PROVIDER)
    mcp = MCPService(storage_service, settings.LLM_MODEL)
    video_service = VideoService(storage_service, queue_service,video_cache_service, mcp)
    query_service = QueryService(mcp,chat_cache_service)

    app.state.queue_service = queue_service
    app.state.query_service = query_service
    app.state.video_cache_service = video_cache_service
    app.state.chat_cache_service = chat_cache_service
    app.state.video_service = video_service

    await app.state.video_cache_service.initialize()
    await app.state.chat_cache_service.initialize()
    await app.state.queue_service.initialize()
    await app.state.query_service.initialize()

    # Start workers  
    await video_service.start(num_workers=1) # GPU safe = 1 worker


    logger.info("API gateway started")

    yield  # The app runs here

    # --- SHUTDOWN LOGIC ---
    logger.info("Shutting down workers...")
    
    # End the worker loops
    await video_service.end()
    
    # Close connections
    await app.state.video_cache_service.close()
    await app.state.chat_cache_service.close()
    logger.info("Cleanup complete. API stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Video Analytics API",
        version="1.0.0",
        description="API gateway for video analytics services",
        docs_url="/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
        lifespan=lifespan,
    )


    # Mount the 'data' directory to the '/static/data' path
    # This allows <img src="/static/data/thumbnails/abc.jpg"> to work
    # Mount it so http://localhost:8000/static/thumbnails/video_id.jpg works
    app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")


    app.add_middleware(
        CORSMiddleware,
        allow_origins=[*settings.CORS_ORIGINS,
                       "http://localhost:5000", "http://127.0.0.1:5000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    app.include_router(home_routes.router,
                       prefix="/api/v1/home", tags=["home"])
    app.include_router(video_routes.router,
                       prefix="/api/v1/videos", tags=["videos"])
    app.include_router(query_routes.router,
                       prefix="/api/v1/query", tags=["query"])
    app.include_router(health_routes.router,
                       prefix="/api/v1/health", tags=["health"])

    return app


app = create_app()
