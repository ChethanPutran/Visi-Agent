"""
Text summarization
"""
from typing import Dict, Any, List, Optional
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from src.services.llm_service.app.llm_service import LLMService

logger = get_logger(__name__)


class TextSummarizer:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def generate_summary(self,video_id, transcript: Dict[str, Any], 
                            frames_data: Optional[List[Dict]] = None) -> str:
        """Generate video summary from transcript and frames"""
        return await self.llm_service.generate_summary(video_id,transcript,frames_data)