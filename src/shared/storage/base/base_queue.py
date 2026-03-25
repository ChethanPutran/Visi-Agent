from abc import ABC, abstractmethod
from typing import Optional

class QueueProvider(ABC):
    """Abstract base class for Queue providers"""
    @abstractmethod
    async def push(self, item: dict):
        """Push an item to the queue"""
        pass
    
    @abstractmethod
    async def pop(self) -> Optional[dict]:
        """Pop an item from the queue. Returns None if the queue is empty."""
        pass

    @abstractmethod
    async def get_size(self) -> int:
        """Get the current size of the queue"""
        pass
    @abstractmethod
    async def health_check(self) -> dict:
        return {
            "healthy": True,
            "service": self.__class__.__name__
        }
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all items from the queue"""
        pass
    @abstractmethod
    async def save_state(self) -> bool:
        """Save the current state of the queue (for in-memory implementations)"""
        pass
    
    @abstractmethod
    async def load_state(self) -> bool:
        """Load the state of the queue (for in-memory implementations)"""
        pass