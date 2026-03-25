from typing import Optional
import redis
import json
from src.shared.logging.logger import get_logger
from ...base import QueueProvider

logger = get_logger(__name__)

class RedisQueue(QueueProvider):
    def __init__(self, queue_name: str, host: str = "localhost", port: int = 6379):
        self.queue_name = queue_name
        self.client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True
            )
  
    async def push(self, item: dict):
        await self.client.lpush(self.queue_name, json.dumps(item))

    async def pop(self) -> Optional[dict]:
        _, job_data = await self.client.brpop(self.queue_name)
        return json.loads(job_data) if job_data else None

    async def get_size(self) -> int:
        size = await self.client.llen(self.queue_name)
        return size
    
    async def clear(self)->bool:
        try:
            await self.client.delete(self.queue_name)
            return True
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return False
    
    async def save_state(self) -> bool:
        return True  # Redis handles persistence, so we can return True here
    
    async def load_state(self) -> bool:
        return True  # Redis handles persistence, so we can return True here
    
    async def health_check(self) -> dict:
        try:
            pong = self.client.ping()
            return {"healthy": pong}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"healthy": False, "error": str(e)}