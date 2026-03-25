import os
from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
from ...base.base_vector_store import VectorStoreProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class ChromaVectorProvider(VectorStoreProvider):
    def __init__(
        self, 
        embedding_model: Any, 
        persist_directory: str = "data/vectors", 
        collection_name: str = "default_collection"
    ):
        """
        Initializes the Chroma provider.
        :param embedding_model: The LangChain-compatible embedding model instance.
        """
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize the vector store (loads if exists, creates if not)
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_model,
            persist_directory=self.persist_directory
        )
        logger.info(f"Chroma initialized at {persist_directory} in collection {collection_name}")

    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """
        Standardizes the input to match the Pinecone style:
        vectors: [{'id': '...', 'values': [embedding], 'metadata': {...}}]
        Note: Chroma typically uses documents/embeddings directly.
        """
        try:
            ids = [v['id'] for v in vectors]
            metadatas = [v['metadata'] for v in vectors]
            embeddings = [v['values'] for v in vectors]
            
            # Since we are using an abstraction, we assume 'values' contains the embedding
            self.vector_store.add_embeddings(
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully upserted {len(vectors)} vectors to Chroma.")
        except Exception as e:
            logger.error(f"Chroma upsert failed: {e}")
            raise

    async def query_vectors(self, query_vector: List[float], top_k: int = 5, 
                            filters: Optional[Dict[str, Any]] = None, 
                            namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # Chroma filters use a slightly different syntax than Pinecone, 
            # but standard dicts often work for simple equality.
            results = self.vector_store.similarity_search_by_vector(
                embedding=query_vector,
                k=top_k,
                filter=filters
            )
            
            return [
                {
                    "id": getattr(doc, 'id', None),
                    "metadata": doc.metadata,
                    "content": doc.page_content  # Chroma stores text in page_content
                } for doc in results
            ]
        except Exception as e:
            logger.error(f"Chroma query failed: {e}")
            return []

    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None):
        try:
            self.vector_store.delete(ids=ids)
            logger.info(f"Deleted IDs {ids} from Chroma")
        except Exception as e:
            logger.error(f"Chroma deletion failed: {e}")

    async def delete_all(self, namespace: Optional[str] = None):
        """Resets the collection"""
        try:
            self.vector_store.delete_collection()
            # Re-initialize after deletion to keep the object valid
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_model,
                persist_directory=self.persist_directory
            )
        except Exception as e:
            logger.error(f"Failed to clear Chroma collection: {e}")