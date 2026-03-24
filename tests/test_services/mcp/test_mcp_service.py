

from src.shared.storage.cache_service import CacheService
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


def test_video_service():
    from src.services.video_ingestion.app.handlers.video_service import VideoService
    from src.services.llm_service.app.mcp_service import MCPManager
    from src.shared.storage.storage_service import StorageService

    store = StorageService("local")
    mcp = MCPManager(store, model="google")


async def test_mcp_service():
    from src.shared.storage.storage_service import StorageService
    from src.services.llm_service.app.mcp_service import MCPManager

    store = StorageService("local")
    mcp = MCPManager(store, model="google")

    TEST_VIDEO_ID = "59dd53dc-6916-4706-8ca1-6328b852bbdb"
    res = await mcp.load_video(TEST_VIDEO_ID)
    logger.info(f"Load Video Result: {res}")

    print(mcp.list_sessions())

# async def test_video_service():
#     video_path = "data/videos/test_video.mp4"

        
#     ss = StorageService("local")
#     mcp = MCPManager(ss,model="google")
#     mcp.analyze_frames_batch('1',
#                              [])
#     logger.info(f"Transcription Result: {res["text"]}")
#     assert res is not None


if __name__ == "__main__":
    test_mcp_service()
    