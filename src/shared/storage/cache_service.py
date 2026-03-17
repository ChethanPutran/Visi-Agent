import asyncio
import json
from typing import Optional, Any
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.logging.logger import get_logger
from typing import Dict

logger = get_logger(__name__)

class CacheService:
    def __init__(self, cache_provider: str = "in_memory"):
        if cache_provider == "redis":
            import redis.asyncio as redis_async
            self.cache = redis_async.Redis(host="localhost", port=6379, decode_responses=True)
        else:
            self.cache = {}
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize cache service"""
        logger.info("CacheService initialized")

    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        
    async def get(self, key: str) -> Optional[VideoMetadata | VideoProcessingStatus]:
        """Get value from cache"""
        logger.debug(f"Cache: {self.cache}")
        logger.info(f"Get Key : {key} from Cache.")
        async with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if expiry is None or expiry > asyncio.get_event_loop().time():
                    return value
                else:
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        logger.debug(f"Cache: {self.cache}")
        logger.info(f"Adding Key: value {key}:{value} to Cache.")
        async with self.lock:
            expiry = None
            if ttl > 0:
                expiry = asyncio.get_event_loop().time() + ttl
            self.cache[key] = (value, expiry)
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        logger.info(f"Delete Key : {key} from Cache.")
        logger.debug(f"Cache: {self.cache}")
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache"""
        async with self.lock:
            self.cache.clear()
            return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Cache health check"""
        return {
            "healthy": True,
            "service": "cache_service",
            "size": len(self.cache),
            "timestamp": asyncio.get_event_loop().time()
        }


class VideoCaheService(CacheService):
    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        data = await self.get(f"video:{video_id}:status")
        if data:
            return json.loads(data)

    async def set_video_status(self, video_id: str, status: VideoProcessingStatus):
        """Set processing status of a video"""
        await self.set(
            key=f"video:{video_id}:status",
            value=json.dumps(status.model_dump())
        )
    async def remove_video_status(self, video_id: str):
        """Remove processing status of a video"""
        await self.delete(f"video:{video_id}:status")

    async def get_video_metadata(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        data = await self.get(f"video:{video_id}:metadata")
        if data:
            return json.loads(data)
        
    async def set_video_metadata(self, video_id: str, metadata: VideoMetadata):
        """Set processing status of a video"""
        await self.set(
            key=f"video:{video_id}:metadata",
            value=json.dumps(metadata.model_dump())
        )

    async def remove_video_metadata(self, video_id: str):
        """Set processing status of a video"""
        await self.delete(
            key=f"video:{video_id}:metadata"
        )