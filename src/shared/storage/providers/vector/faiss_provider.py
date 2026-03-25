import os
import asyncio
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from ...base.base_vector_store import VectorStoreProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class FaissVectorProvider(VectorStoreProvider):
    def __init__(
        self, 
        embedding_model: Any, 
        persist_directory: str = "data/vectors", 
        collection_name: str = "default_collection"
    ):
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.stores: Dict[str, FAISS] = {}  # Cache: namespace -> FAISS instance
        
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory)

    def _get_index_path(self, namespace: Optional[str]) -> str:
        name = namespace or self.collection_name
        return os.path.join(self.persist_directory, f"faiss_{name}")

    async def _get_or_load_store(self, namespace: Optional[str]) -> FAISS:
        """Helper to get store from cache or disk."""
        ns_key = namespace or self.collection_name
        
        if ns_key in self.stores:
            return self.stores[ns_key]

        path = self._get_index_path(namespace)
        if os.path.exists(path):
            # Load existing
            store = await asyncio.to_thread(
                FAISS.load_local, path, self.embedding_model, allow_dangerous_deserialization=True
            )
            self.stores[ns_key] = store
            return store
        
        raise ValueError(f"Vector store for {ns_key} does not exist. Create it first.")

    async def create_vector_from_documents(self, documents: List[Document], namespace: Optional[str] = None) -> bool:
        """Creates and SAVES a new FAISS index."""
        try:
            # FAISS.from_documents is a class method that returns a new instance
            vector_store = await asyncio.to_thread(
                FAISS.from_documents, documents, self.embedding_model
            )
            
            # Save to disk immediately
            path = self._get_index_path(namespace)
            await asyncio.to_thread(vector_store.save_local, path)
            
            # Update cache
            ns_key = namespace or self.collection_name
            self.stores[ns_key] = vector_store
            
            logger.info(f"FAISS index created and saved at {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create FAISS from documents: {e}")
            return False

    async def query_vectors(self, query_vector: List[float], top_k: int = 5, 
                            filters: Optional[Dict[str, Any]] = None, 
                            namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            store = await self._get_or_load_store(namespace)
            
            # FAISS uses similarity_search_with_score_by_vector
            results = await asyncio.to_thread(
                store.similarity_search_with_score_by_vector,
                embedding=query_vector,
                k=top_k,
                filter=filters
            )
            
            return [
                {
                    "id": getattr(doc, 'id', None),
                    "metadata": doc.metadata,
                    "content": doc.page_content,
                    "score": float(score)
                } for doc, score in results
            ]
        except Exception as e:
            logger.error(f"FAISS query failed: {e}")
            return []

    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """Adds vectors and persists the change."""
        try:
            store = await self._get_or_load_store(namespace)
            
            # LangChain FAISS doesn't have a direct 'add_embeddings' with IDs easily,
            # we typically convert to Documents for consistency
            texts = [v['metadata'].get('text', '') for v in vectors]
            metadatas = [v['metadata'] for v in vectors]
            ids = [v['id'] for v in vectors]
            
            store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            
            # Critical: Persist changes
            await asyncio.to_thread(store.save_local, self._get_index_path(namespace))
            logger.info(f"Upserted {len(vectors)} vectors and saved FAISS index.")
        except Exception as e:
            logger.error(f"FAISS upsert failed: {e}")
            raise

    async def vector_store_exists(self, namespace: str | None = None) -> bool:
        path = self._get_index_path(namespace)
        # FAISS saves an index.faiss and index.pkl file
        return os.path.exists(os.path.join(path, "index.faiss"))