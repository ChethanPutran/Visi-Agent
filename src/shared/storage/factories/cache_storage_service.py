from src.shared.config.settings import settings, CacheProviders
from src.shared.storage.base import CacheProvider
from src.shared.storage.providers.cache import LocalCache,RedisCache
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class CacheService:
    """Unified storage service with provider abstraction"""
    
    _instance = None
    _provider:CacheProvider

    def __init__(self, provider: str):
        if self._initialized:
            return
        
        if provider == CacheProviders.LOCAL:
            self._provider = LocalCache(settings.CACHE_STORAGE_PATH)
            logger.info(f"Using local cache at {settings.CACHE_STORAGE_PATH}")
        elif provider == CacheProviders.REDIS:
            self._provider = RedisCache(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DECODE_RESPONSES)
            logger.info(f"Using Redis cache")
        else:
            raise ValueError(f"Unsupported cache provider: {provider}")

        self._initialized = True

    # Singleton pattern   
    def __new__(cls, storage_provider: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @property
    def provider(self) -> CacheProvider:
        """Get the current storage provider"""
        return self._provider 
    