from src.shared.config.settings import settings
from src.shared.storage.base.base_vector_store import VectorStoreProvider
from src.shared.storage.providers.vector.chroma_provider import ChromaVectorProvider
from src.shared.storage.providers.vector.pinecone_provider import PineconeVectorProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class VectorStoreProviders:
    CHROMA="chroma"
    PINECONE="pinecone"
    LOCLAL="local"

class VectorStoreService:
    """Unified vector store service with provider abstraction"""
    
    _instance = None
    _provider:VectorStoreProvider

    def __init__(self, provider: str):
        if self._initialized:
            return
        
        if provider == VectorStoreProviders.CHROMA:
            self._provider = ChromaVectorProvider(
                embedding_model=settings.CHROMA_EMBEDDING_MODEL,
                collection_name=settings.CHROMA_COLLECTION_NAME,
                persist_directory=settings.CHROMA_PERSISTENT_DIR
            )
        elif provider == VectorStoreProviders.PINECONE:
            assert settings.PINECONE_INDEX_NAME and settings.PINECONE_API_KEY and settings.PINECONE_ENVIRONMENT, "Pinecone settings must be configured"
            self._provider = PineconeVectorProvider(
                index_name=settings.PINECONE_INDEX_NAME,
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
        else:
            raise ValueError(f"Unsupported vector store provider: {provider}")

        logger.info(f"Using local vector store at {settings.VECTOR_DB_PATH}")
        self._initialized = True

    # Singleton pattern   
    def __new__(cls, storage_provider: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @property
    def provider(self) -> VectorStoreProvider:
        """Get the current vector store provider"""
        return self._provider 
    
    
   