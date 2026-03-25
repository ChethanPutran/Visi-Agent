import asyncio
from typing import Optional, Any, Dict
import redis.asyncio as redis_async
from src.shared.logging.logger import get_logger
from src.shared.storage.base.base_cache import CacheProvider

logger = get_logger(__name__)

class RedisCache(CacheProvider):
    def __init__(self, host: str, port: int = 300, decode_responses: bool = True):
        self.cache = redis_async.Redis(host=host, port=port, decode_responses=decode_responses)
        self.lock = asyncio.Lock()

    async def initialize(self):
        """Initialize cache service"""
        logger.info(f"CacheService initialized with provider: {type(self.cache).__name__}")
        # self._save_task = asyncio.create_task(self._periodic_save())
        pass
             
    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        pass 
    
    async def save(self):
        pass

    async def load(self):
        pass 
        

    async def get(self, key: str) -> Optional[str]:
        return await self.cache.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        await self.cache.set(key, value, ex=ttl)
        return True
        
    # New Atomic Increment for the counter
    async def increment(self, key: str) -> int:
        return await self.cache.incr(key)
    
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
            await self.cache.flushdb()
            return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Cache health check"""
        return {
            "healthy": self.cache.ping(),
            "service": "cache_service",
            "size": await self.cache.dbsize(),
            "timestamp": asyncio.get_event_loop().time()
        }
    