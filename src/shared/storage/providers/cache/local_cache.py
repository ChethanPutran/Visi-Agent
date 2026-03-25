import asyncio

from ...base import CacheProvider
from src.shared.logging.logger import get_logger
from typing import Dict, Any, Optional
import json
import time

logger = get_logger(__name__)

class LocalCache(CacheProvider):
    def __init__(self, storage_path: str,save_interval: int = 300):
        self.cache = {}  # In-memory cache

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
            await self.save()
                
    async def close(self):
        """Close cache service"""
        logger.info("CacheService closed")
        await self.save()  # Ensure in-memory cache is saved if needed
    
    async def save(self):
        """Save in-memory cache to disk (if using in-memory)"""
        with open(self.storage_path + f"/cache_backup.json", "w") as f:
            json.dump(self.cache, f)

    async def load(self):
        """Load in-memory cache from disk (if using in-memory)"""
        with open(self.storage_path + f"/cache_backup.json", "r") as f:
            self.cache = json.load(f)
        

    async def get(self, key: str) -> Optional[str]:
        async with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if expiry is None or expiry > time.time():
                    return value
                del self.cache[key]
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        async with self.lock:
            expiry = time.time() + ttl if ttl > 0 else None
            self.cache[key] = (value, expiry)
            return True
        
    # Increment for the counter
    async def increment(self, key: str) -> int:
        async with self.lock:
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