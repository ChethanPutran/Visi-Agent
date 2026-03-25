from src.shared.config.settings import settings, StorageProviders
from src.shared.storage.base.base_storage import StorageProvider
from src.shared.storage.providers.blobs.local_storage import LocalStorageProvider
from src.shared.storage.providers.blobs.s3_provider import S3StorageProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class BlobStorageService:
    """Unified storage service with provider abstraction"""
    
    _instance = None
    _provider:StorageProvider

    def __init__(self, storage_provider: str):
        if self._initialized:
            return
        
        if storage_provider == StorageProviders.LOCAL:
            self._provider = LocalStorageProvider(settings.STORAGE_PATH)
        elif storage_provider == StorageProviders.S3:
            # Placeholder for remote provider initialization (e.g. S3, GCS)
            self._provider = S3StorageProvider()
        else:
            raise ValueError(f"Unsupported storage provider: {storage_provider}")

        logger.info(f"Using local storage at {settings.STORAGE_PATH}")
        self._initialized = True

    # Singleton pattern   
    def __new__(cls, storage_provider: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @property
    def provider(self) -> StorageProvider:
        """Get the current storage provider"""
        return self._provider 
    
    
   