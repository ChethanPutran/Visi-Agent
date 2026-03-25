from datetime import datetime
from typing import Dict, Any

from src.shared.storage.repository.chat_repository import ChatRepository
from src.shared.logging.logger import get_logger
from src.services.llm_service.app.llm_service import LLMService

logger = get_logger(__name__)

class QueryService:
    """Service for handling query operations"""

    def __init__(self, llm_service: LLMService, repository: ChatRepository):
        # Initialize any required resources, e.g., database connections
        self.llm_service = llm_service
        self.repository = repository

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
        
        history = await self.repository.get_chat_history(video_id)  

        if history:
            messages = history + [
                {"role": "user", "content": question}
            ]
        else:
            messages = [
                {"role": "system", "content": f"You are an assistant that answers questions in 1-2 sentences."},
                {"role": "user", "content": question}
            ]
            
        result = await self.llm_service.chat(
            question=question,
            chat_history=messages,
            video_id=video_id)
        
        result["answer"] = result.get("answer", "No answer found")

        if include_timestamps and "timestamps" not in result:
            result["timestamps"] = result.get("timestamps", [])
            
        result["confidence"] = result.get("confidence", 0.0)
        result["sources"] = result.get("sources", [])

        messages.append({"role": "assistant", "content": result["answer"]})
        
        await self.repository.set_chat_history(video_id, messages)
         
        return result
    
    async def get_chat_history(self,
                           video_id: str):
        
        history = await self.repository.get_chat_history(video_id) 

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
