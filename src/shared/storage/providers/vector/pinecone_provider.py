from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import SecretStr
from pinecone import Pinecone

from src.shared.logging.logger import get_logger
from src.shared.config.settings import settings

from ...base.base_vector_store import VectorStoreProvider

logger = get_logger(__name__)

class PineconeVectorProvider(VectorStoreProvider):
    def __init__(self, index_name: str, api_key: SecretStr, environment: str):
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index = self.pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")

    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None):
        """
        Expects vectors in format: 
        {'id': 'val', 'values': [...], 'metadata': {...}}
        """
        try:
            # Pinecone upsert is synchronous in the SDK, but we wrap it
            self.index.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {e}")
            raise

    async def query_vectors(self, query_vector: List[float], top_k: int = 5, 
                            filters: Optional[Dict[str, Any]] = None, 
                            namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filters,
                namespace=namespace,
                include_metadata=True
            )
            # Standardize output format
            return [
                {
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match["metadata"]
                } for match in response["matches"]
            ]
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            return []

    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None):
        self.index.delete(ids=ids, namespace=namespace)

    async def delete_all(self, namespace: Optional[str] = None):
        self.index.delete(delete_all=True, namespace=namespace)


        from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="YOUR_API_KEY")

# Create a serverless index
if 'video-search' not in pc.list_indexes().names():
    pc.create_index(
        name='video-search',
        dimension=1536, # Standard for OpenAI embeddings
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )

index = pc.Index("video-search")

def index_video_segments(self, video_id, processed_frames_data):
    vectors_to_upsert = []
    
    for segment in processed_frames_data:
        # 1. Generate an embedding for the LLM description
        # (Assuming you have a self.get_embedding helper)
        description_vector = self.get_embedding(segment['description'])
        
        # 2. Prepare the record
        vectors_to_upsert.append({
            "id": f"{video_id}_{segment['start']}",
            "values": description_vector,
            "metadata": {
                "video_id": video_id,
                "start_time": segment['start'],
                "end_time": segment['end'],
                "description": segment['description'],
                "original_caption": segment['caption']
            }
        })
    
    # 3. Batch upload to Pinecone
    index.upsert(vectors=vectors_to_upsert)