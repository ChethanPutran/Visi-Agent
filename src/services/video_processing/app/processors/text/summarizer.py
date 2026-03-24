"""
Text summarization
"""
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from src.services.llm_service.app.mcp_service import MCPService

logger = get_logger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class TextSummarizer:
    def __init__(self, mcp_manager: MCPService) -> None:
        self.mcp_manager = mcp_manager

    async def generate_summary(self,video_id, transcript: Dict[str, Any], 
                            frames_data: Optional[List[Dict]] = None) -> str:
        """Generate video summary from transcript and frames"""
        return self.mcp_manager.generate_summary(video_id,transcript,frames_data)