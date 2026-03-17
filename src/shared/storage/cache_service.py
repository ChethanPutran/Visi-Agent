import asyncio
from typing import Optional, Any
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.logging.logger import get_logger
from typing import Dict

logger = get_logger(__name__)

class CacheService:
    def __init__(self):
        self.cache = {}
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize cache service"""
        logger.info("CacheService initialized")

    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        
    async def get(self, key: str) -> Optional[VideoMetadata]:
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
