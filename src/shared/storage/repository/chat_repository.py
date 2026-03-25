
import json
from typing import List, Optional 
from src.shared.storage.base.base_cache import CacheProvider
from src.shared.storage.base.base_storage import StorageProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class ChatRepository:
    def __init__(self, storage: StorageProvider, cache: CacheProvider):
        self.storage = storage
        self.cache = cache
    
    async def save_chat_history(self, video_id: str, history: List[dict[str, str]]):
        """Save chat history for a video"""
        # Save to storage
        await self.storage.save_file(history, f"chat/{video_id}/history.json")

        # Update cache
        await self.set_chat_history(video_id, history)

    async def get_chat_history(self, video_id: str) -> Optional[List[dict[str, str]]]:
        """Get chat history for a video"""
        history = await self.get_chat_history_from_cache(video_id)
        if history is not None:
            return history

        # If not in cache, load from storage
        history = await self.storage.get_file(f"chat/{video_id}/history.json")
        if history:
            history = json.loads(history)
            # Update cache
            await self.set_chat_history(video_id, history)
        return history

    async def get_chat_history_from_cache(self, video_id: str) -> Optional[List[dict[str, str]]]:
        """Get chat history for a video"""
        # First check cache
        data: Optional[str] = await self.cache.get(f"chat:{video_id}:history")
        if not data:
            return None
        return json.loads(data)
    
    async def set_chat_history(self, video_id: str, history: List[dict[str, str]]):
        await self.cache.set(
            key=f"chat:{video_id}:history",
            value=json.dumps(history),
            ttl=3600 # Cache chat history for 1 hour
        )

