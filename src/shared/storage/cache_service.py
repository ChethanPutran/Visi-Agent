import asyncio
import json
from typing import Optional, Any

import redis
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
        elif cache_provider == "in_memory":
            self.cache = {}  # In-memory cache
        else:
            raise ValueError(f"Unsupported cache provider: {cache_provider}")

        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize cache service"""
        logger.info(f"CacheService initialized with provider: {type(self.cache).__name__}")

    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        # logger.debug(f"Cache: {self.cache}")
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
        # logger.debug(f"Cache: {self.cache}")
        logger.info(f"Adding Key: value {key} to Cache.")

        if isinstance(self.cache, redis.Redis):
            await self.cache.set(key, value, ex=ttl)
            return True
        
        if isinstance(self.cache, dict):
            async with self.lock:
                expiry = None
                if ttl > 0:
                    expiry = asyncio.get_event_loop().time() + ttl
                self.cache[key] = (value, expiry)
                return True
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        logger.info(f"Delete Key : {key} from Cache.")
        # logger.debug(f"Cache: {self.cache}")
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache"""
        async with self.lock:
            if isinstance(self.cache, redis.Redis):
                await self.cache.flushdb()
            if isinstance(self.cache, dict):
                self.cache.clear()
            return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Cache health check"""
        return {
            "healthy": True,
            "service": "cache_service",
            "size": len(self.cache) if isinstance(self.cache, dict) else "N/A",
            "timestamp": asyncio.get_event_loop().time()
        }


class VideoCacheService(CacheService):
    def __init__(self, cache_provider: str = "in_memory"):
        super().__init__(cache_provider)
        
    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        data: Optional[str] = await self.get(f"video:{video_id}:status")

        if not data:
            return None
        try:
            return VideoProcessingStatus.model_validate_json(data)
        except Exception as e:
            # If the data in Redis is corrupt or double-encoded
            logger.error(f"Failed to parse status for {video_id}: {e}")
            return None

    async def set_video_status(self, video_id: str, status: VideoProcessingStatus):
        """Set processing status of a video"""
        await self.set(
            key=f"video:{video_id}:status",
            value=status.model_dump_json()
        )
        
    async def set_video_results(self, video_id: str, results: Dict[str, Any]):
        """Set processing results of a video"""
        await self.set(
            key=f"video:{video_id}:results",
            value=json.dumps(results)
        )
        count  = await self.get_processed_count()
        await self.set_processed_count(count + 1)
        
    async def get_processed_count(self) -> int:
        """Get processed count of a video"""
        data = await self.get(f"video:results:count")
        if data:
            count = json.loads(data)
            return count
        return 0
    async def set_processed_count(self, count: int):
        """Set processed count of a video"""
        await self.set(
            key=f"video:results:count",
            value=json.dumps(count)
        )
        return 0
    
    async def remove_video_status(self, video_id: str):
        """Remove processing status of a video"""
        await self.delete(f"video:{video_id}:status")

    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""
        data: Optional[str] = await self.get(f"video:{video_id}:metadata")

        if not data:
            return None
    
        try:
            return VideoMetadata.model_validate_json(data)
        except Exception as e:
            # If the data in Redis is corrupt or double-encoded
            logger.error(f"Failed to parse metadata for {video_id}: {e}")
            return None

    async def set_video_metadata(self, video_id: str, metadata: VideoMetadata):
        """Set video metadata"""
        await self.set(
            key=f"video:{video_id}:metadata",
            value=metadata.model_dump_json()
        )

    async def remove_video_metadata(self, video_id: str):
        """Remove video metadata"""
        await self.delete(
            key=f"video:{video_id}:metadata"
        )