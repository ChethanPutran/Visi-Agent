import asyncio
import json
from typing import List, Optional, Any
import time
import redis
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.logging.logger import get_logger
from typing import Dict
from src.shared.config.settings import settings

logger = get_logger(__name__)

class CacheService:
    def __init__(self, cache_provider: str = "in_memory", save_interval: int = 300, storage_path: str = settings.CACHE_STORAGE_PATH):
        if cache_provider == "redis":
            import redis.asyncio as redis_async
            self.cache = redis_async.Redis(host="localhost", port=6379, decode_responses=True)
        elif cache_provider == "in_memory":
            self.cache = {}  # In-memory cache
        else:
            raise ValueError(f"Unsupported cache provider: {cache_provider}")

        self.lock = asyncio.Lock()
        self.save_interval = save_interval
        self.storage_path = storage_path


    async def initialize(self):
        """Initialize cache service"""
        logger.info(f"CacheService initialized with provider: {type(self.cache).__name__}")
        # self._save_task = asyncio.create_task(self._periodic_save())
        await self.load()  # Load existing cache if using in-memory

    async def _periodic_save(self):
        """Periodically save in-memory cache to disk"""
        while True:
            await asyncio.sleep(self.save_interval)
            if isinstance(self.cache, dict):
                await self.save()
                
    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        await self.save()  # Ensure in-memory cache is saved if needed
    
    async def save(self):
        """Save in-memory cache to disk (if using in-memory)"""
        if isinstance(self.cache, dict):
            with open(self.storage_path + f"/cache_backup.json", "w") as f:
                json.dump(self.cache, f)

    async def load(self):
        """Load in-memory cache from disk (if using in-memory)"""
        if isinstance(self.cache, dict):
            try:
                with open(self.storage_path + f"/cache_backup.json", "r") as f:
                    self.cache = json.load(f)
            except FileNotFoundError:
                logger.info("No existing cache found.")
        

    async def get(self, key: str) -> Optional[str]:
        # REDIS PATH: No lock needed
        if not isinstance(self.cache, dict):
            return await self.cache.get(key)
        
        # IN-MEMORY PATH: Use lock
        async with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if expiry is None or expiry > time.time():
                    return value
                del self.cache[key]
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        if not isinstance(self.cache, dict):
            await self.cache.set(key, value, ex=ttl)
            return True
        
        async with self.lock:
            expiry = time.time() + ttl if ttl > 0 else None
            self.cache[key] = (value, expiry)
            return True
        
    # New Atomic Increment for the counter
    async def increment(self, key: str) -> int:
        if not isinstance(self.cache, dict):
            return await self.cache.incr(key)
        
        async with self.lock:
            # Fallback for in-memory
            current = int(self.cache.get(key, (0, None))[0])
            new_val = current + 1
            self.cache[key] = (str(new_val), None)
            return new_val
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        # logger.info(f"Delete Key : {key} from Cache.")
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

class ChatCacheService(CacheService):
    def __init__(self, cache_provider: str = "in_memory"):
        super().__init__(cache_provider)
    
    async def get_chat_history_key(self, video_id: str) -> Optional[List[dict[str, str]]]:
        """Get chat history for a video"""
        data: Optional[str] = await self.get(f"chat:{video_id}:history")
        if not data:
            return None
        return json.loads(data)
    
    async def set_chat_history_key(self, video_id: str, history: List[dict[str, str]]):
        await self.set(
            key=f"chat:{video_id}:history",
            value=json.dumps(history),
            ttl=3600 # Cache chat history for 1 hour
        )


class VideoCacheService(CacheService):
    def __init__(self, cache_provider: str = "in_memory"):
        super().__init__(cache_provider)
        
    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        data: Optional[str] = await self.get(f"video:{video_id}:status")
        if not data:
            return None
        try:
            status = VideoProcessingStatus.model_validate_json(data)
            logger.info(f"Get Video Status for {video_id}: {status.current_stage}, {status.progress*100:.2f}%")
            return status
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
        """Set processing results and increment global count atomically"""
        await self.set(
            key=f"video:{video_id}:results",
            value=json.dumps(results),
            ttl=86400 # Extend to 24 hours so users don't lose results immediately
        )
        # This is now thread-safe!
        await self.increment(f"video:results:count")
        
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