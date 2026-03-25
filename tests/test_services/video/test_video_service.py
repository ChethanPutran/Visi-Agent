from src.services.video_ingestion.app.handlers.video_service import VideoService
from src.services.llm_service.app.mcp_service import MCPManager
from src.shared.storage.factories.blob_storage_service import StorageService
from src.shared.storage.providers.cache.redis_cache import CacheService
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


async def test_video_service():
    video_path = "data/videos/test_video.mp4"

        
        
    ss = StorageService("local")
    cs = CacheService()
    mcp = MCPManager(ss,model="google")
    vs = VideoService(ss,cs,mcp)
    res = await vs.process_video("1",video_path)
    logger.info(f"Transcription Result: {res["text"]}")
    assert res is not None