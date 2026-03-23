import redis
from typing import Optional
import json 
from collections import deque
from src.shared.logging.logger import get_logger
from typing import Dict

logger = get_logger(__name__)

class LocalQueueService:
    def __init__(self):
        self.queue = deque()

    async def push(self, item: dict):
        self.queue.append(item)

    async def pop(self) -> Optional[dict]:
        if self.queue:
            return self.queue.popleft()
        return None

class QueueService:
    def __init__(self, provider_type: str, queue_name: str):
        if provider_type == "redis":
            self.queue_name = queue_name
            self.client = redis.Redis(
                host="localhost",
                port=6379,
                decode_responses=True
            )
        elif provider_type == "in_memory":
            self.queue = LocalQueueService()
        else:
            raise ValueError(f"Unsupported queue provider: {provider_type}")

    async def initialize(self):
        logger.info(f"QueueService initialized with provider: {type(self.queue).__name__ if hasattr(self, 'queue') else 'Redis'}")
        
    async def push(self, item: dict):
        if isinstance(self.queue, LocalQueueService):
            await self.queue.push(item)
        else:
            await self.client.lpush(self.queue_name, json.dumps(item))

    async def pop(self) -> dict:
        if isinstance(self.queue, LocalQueueService):
            item  = await self.queue.pop()
            return item if item else {}
        else:
            _, job_data = await self.client.brpop(self.queue_name)
            return json.loads(job_data)
    
    async def get_size(self) -> int:
        if isinstance(self.queue, LocalQueueService):
            return len(self.queue.queue)
        else:
            size = await self.client.llen(self.queue_name)
            return size