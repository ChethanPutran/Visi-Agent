import redis
from typing import Optional
import json 


class QueueService:
    def __init__(self, provider_type: str, queue_name: str):
        if provider_type == "redis":
            self.queue_name = queue_name
            self.client = redis.Redis(
                host="localhost",
                port=6379,
                decode_responses=True
            )
        else:
            raise ValueError(f"Unsupported queue provider: {provider_type}")
        
    async def push(self, item: dict):
        await self.client.lpush(self.queue_name, json.dumps(item))

    async def pop(self) -> dict:
        _, job_data = await self.client.brpop(self.queue_name)
        return json.loads(job_data)