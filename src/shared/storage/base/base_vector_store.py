from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

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