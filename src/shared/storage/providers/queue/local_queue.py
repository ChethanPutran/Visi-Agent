from typing import Any, Dict, Optional
from collections import deque
from src.shared.logging.logger import get_logger
from ...base import QueueProvider

logger = get_logger(__name__)

class LocalQueue(QueueProvider):
    def __init__(self):
        self.queue = deque()

    async def push(self, item: dict):
        self.queue.append(item)

    async def pop(self) -> Optional[dict]:
        if self.queue:
            return self.queue.popleft()
        return None

    async def get_size(self) -> int:
        return len(self.queue)
    
    async def clear(self)-> bool:
        try:
             self.queue.clear()
             return True
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Queue health check"""
        return {
            "healthy": True,
            "service": "local_queue",
            "size": len(self.queue)
        }
    async def save_state(self) -> bool:
        return await super().save_state()
    
    async def load_state(self) -> bool:
        return await super().load_state()
    
    