import redis
from typing import Optional
import json 
from collections import deque
from src.shared.logging.logger import get_logger
from typing import Dict
from src.shared.config.settings import QueueProviders, settings, StorageProviders
from src.shared.storage.providers.queue import LocalQueue,RedisQueue
from src.shared.storage.base import QueueProvider
logger = get_logger(__name__)


class QueueService:
    """Unified storage service with provider abstraction"""
    
    _instance = None
    _provider:QueueProvider

    def __init__(self, provider_type: str, queue_name: str):
        if self._initialized:
            return
        
        if provider_type == QueueProviders.LOCAL:
            self._provider = LocalQueue()
        elif provider_type == QueueProviders.REDIS:
            self._provider = RedisQueue(
                queue_name=queue_name,
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT
            )  
        else:
            raise ValueError(f"Unsupported queue provider: {provider_type}")

        logger.info(f"Using queue with provider: {provider_type}")
        self._initialized = True

    # Singleton pattern   
    def __new__(cls, queue_provider: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @property
    def provider(self) -> QueueProvider:
        """Get the current queue provider"""
        return self._provider 
    
    
   