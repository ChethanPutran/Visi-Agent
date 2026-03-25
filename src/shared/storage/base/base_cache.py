from typing import Optional
from abc import ABC, abstractmethod

class CacheProvider(ABC):
    """Abstract base class for cache providers"""
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache by key"""
        pass
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with optional TTL"""
        pass
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache"""
        pass
    @abstractmethod
    async def increment(self, key: str) -> int:
        """Increment value in cache"""
        pass
    @abstractmethod
    async def close(self) -> int:
        """Close cache connection"""
        pass
