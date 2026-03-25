from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class VectorStore(ABC):
    """Represents a vector store instance for a specific video."""
    @abstractmethod
    async def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform a similarity search for the given query."""
        pass
    
class VectorStoreProvider(ABC):
    """Abstract base class for Vector Database providers"""

    @abstractmethod
    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """Insert or update vectors with metadata"""
        pass

    @abstractmethod
    async def query_vectors(self, query_vector: List[float], top_k: int = 5, 
                            filters: Optional[Dict[str, Any]] = None, 
                            namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass

    @abstractmethod
    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None):
        """Delete specific vectors by ID"""
        pass

    @abstractmethod
    async def delete_all(self, namespace: Optional[str] = None):
        """Clear a namespace or index"""
        pass

    @abstractmethod
    async def vector_store_exists(self, namespace: Optional[str] = None)-> bool:
        """Check if a vector store index exists in the namespace"""
        pass

    
    @abstractmethod
    async def create_vector_store(self, namespace: Optional[str] = None):
        """Initialize a new vector store index"""
        pass

    @abstractmethod
    async def get_vector_store(self, namespace: Optional[str] = None)-> VectorStore:
        """Initialize a new vector store index"""
        pass

    @abstractmethod
    async def create_vector_from_documents(self, documents: List[Any], namespace: Optional[str] = None)->bool:
        """Initialize a new vector store index from a list of documents"""
        pass
