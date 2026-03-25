from datetime import datetime
from typing import Dict, Any

from src.shared.storage.providers.cache.redis_cache import ChatCacheService
from src.shared.logging.logger import get_logger
from src.services.llm_service.app.mcp_service import MCPService

logger = get_logger(__name__)

class QueryService:
    """Service for handling query operations"""

    def __init__(self, mcp_service: MCPService, cache_service: ChatCacheService):
        # Initialize any required resources, e.g., database connections
        self.mcp_service = mcp_service
        self.cache_service = cache_service

    async def initialize(self):
        """Initialize any resources if needed"""
        logger.info("Initializing QueryService")

    async def execute_query(self, query: str) -> dict:
        """Execute a query and return results"""
        # Placeholder implementation
        # In a real implementation, this would interact with a database or search engine
        return {"query": query, "results": []}

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        return {
            "healthy": True,
            "service": "query_service",
            "timestamp": datetime.now()
        }

    async def ask_question(self,
                           video_id: str,
                           question: str,
                           include_timestamps: bool,
                           max_results: int
                           ):
        
        history = await self.cache_service.get_chat_history_key(video_id)  

        if history:
            messages = history + [
                {"role": "user", "content": question}
            ]
        else:
            messages = [
                {"role": "system", "content": f"You are an assistant that answers questions in 1-2 sentences."},
                {"role": "user", "content": question}
            ]
            
        result = await self.mcp_service.chat(
            question=question,
            chat_history=messages,
            video_id=video_id)
        
        result["answer"] = result.get("answer", "No answer found")

        if include_timestamps and "timestamps" not in result:
            result["timestamps"] = result.get("timestamps", [])
            
        result["confidence"] = result.get("confidence", 0.0)
        result["sources"] = result.get("sources", [])

        messages.append({"role": "assistant", "content": result["answer"]})
        
        await self.cache_service.set_chat_history_key(video_id, messages)
         
        return result
    
    async def get_chat_history(self,
                           video_id: str):
        
        history = await self.cache_service.get_chat_history_key(video_id) 

        # Exclude the system prompt and return only user-assistant interactions
        history_except_first = history[1:] if history and len(history) > 1 else [] 
         
        return history_except_first

    async def query_temporal_range(self,
                                   video_id: str,
                                   start_time: float,
                                   end_time: float,
                                   detail_level: str
                                   ):
        return {}

    async def compare_timeframes(
        self,
        video_id: str,
        timeframe1: tuple,
        timeframe2: tuple
    ):
        return {}

    async def search_content(
        self,
        video_id: str,
        query: str,
        search_type: str,
        limit: int,
        threshold: float
    ):
        return {}

    async def get_query_suggestions(self, video_id: str):
        return {}

    async def query_multiple_videos(
        self,
        video_ids: list,
        question: str
    ):
        return {}
