import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from src.services.llm_service.app.agent.core.video_agent import VideoAnalyticsAgent
from src.shared.config.settings import LLMModels
from src.shared.storage.repository import VideoRepository, ChatRepository
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

@dataclass
class VideoSession:
    """Represents a video loaded in MCP"""
    video_id: str
    agent: VideoAnalyticsAgent
    metadata: VideoMetadata
    loaded_at: datetime
    query_count: int = 0
    last_query_time: Optional[datetime] = None


class LLMService:
    """Manages MCP video sessions with persistence"""
    _instance: Optional["LLMService"] = None

    def __init__(self, video_repo: VideoRepository, model: LLMModels = LLMModels.GEMINI):
        if self._initialized:
            return

        self._model = model
        self.video_repo = video_repo
        self.sessions: Dict[str, VideoSession] = {}
        self.agent_pool: Dict[str, VideoAnalyticsAgent] = {}
        self._initialized = True
        logger.info(f"Using model: {model}")
        
    def __new__(cls, video_repo: VideoRepository, model: LLMModels = LLMModels.GEMINI):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance


    @property
    def model(self) -> LLMModels:
        return self._model
    
    async def _get_agent(self,video_id):
        # Create or reuse agent
        agent = self.agent_pool.get(video_id)
        if not agent:
            agent = VideoAnalyticsAgent(self.model)
            self.agent_pool[video_id] = agent
        return agent


    async def load_video(self, video_id: str, auto_load: bool = True) -> Dict[str, Any]:
        """Load a video into MCP session"""
        try:
            # Check if already loaded
            if video_id in self.sessions:
                return {
                    "success": True,
                    "message": f"Video {video_id} already loaded",
                    "session": self.sessions[video_id].__dict__
                }
            
            # Get video data from storage
            transcript = await self.video_repo.get_transcript(video_id)
            frames_data = await self.video_repo.get_frames_data(video_id)
            metadata = await self.video_repo.get_video_metadata(video_id)

            if not transcript or not frames_data or metadata is None:
                return {
                    "success": False,
                    "error": "Video not fully processed or data not found"
                }

            # Parse data
            if isinstance(transcript, str):
                transcript = json.loads(transcript)

            if isinstance(frames_data, str):
                frames_data = json.loads(frames_data)

          
            agent = await self._get_agent(video_id)


            # Create session
            session = VideoSession(
                video_id=video_id,
                agent=agent,
                metadata=metadata,
                loaded_at=datetime.now()
            )

            # Update agent state
            store = await self.video_repo.get_vector_store(video_id)  # Ensure vector store is initialized
            
            agent.load_video(store)

            # Convert VideoMetadata to dict and store in agent for easy access
            agent.video_metadata = vars(session.metadata)

            # Store session
            self.sessions[video_id] = session

            logger.info(f"Loaded video {video_id} into MCP session")

            return {
                "success": True,
                "message": f"Video {video_id} loaded successfully",
                "session_id": video_id,
                "metadata": session.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to load video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query_video(self, video_id: str, question: str) -> Dict[str, Any]:
        """Query a video session"""
        
        if video_id not in self.sessions:
            # Try auto-load
            load_result = await self.load_video(video_id)
            if not load_result["success"]:
                return {
                    "success": False,
                    "error": f"Video {video_id} not loaded: {load_result.get('error', 'Unknown error')}"
                }
        
        session = self.sessions[video_id]
        
        try:
            # Execute query
            response = await session.agent.query_video(question)
            
            # Update session stats
            session.query_count += 1
            session.last_query_time = datetime.now()
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "video_id": video_id
            }

    async def chat(self,question:str, chat_history: List[Dict[str, Any]], video_id: Optional[str] = None) -> Dict[str, Any]:
        """Chat with the agent, optionally in the context of a video"""
        if video_id:
            if video_id not in self.sessions:
                load_result = await self.load_video(video_id)
                if not load_result["success"]:
                    return {
                        "success": False,
                        "error": f"Video {video_id} not loaded: {load_result.get('error', 'Unknown error')}"
                    }
            session = self.sessions[video_id]
            response = await session.agent.chat(question, chat_history, video_id)

        else:
            # General chat without video context
            agent = VideoAnalyticsAgent(self.model)
            response = await agent.chat(question, chat_history)
            
        return response
        
    async def generate_summary(self, video_id: str, transcript: Dict[str, Any], frames_data: Optional[List[Dict]] = None) -> str:
        """Generate video summary from transcript and frames"""
        agent = await self._get_agent(video_id)
        return await agent.generate_summary(video_id, transcript, frames_data)

if __name__ == "__main__":    # Example usage
    # from src.shared.storage.providers import ChromaVectorProvider, LocalStorageProvider
    # from src.shared.config.settings import StorageProviders, LLMModel

    # video_repo = VideoRepository(storage=LocalStorageProvider())
    # mcp_service = MCPService(video_repo, model=LLMModel.GEMINI)

    # VIDEO_ID = "8bf5d8af-aa6d-4ae1-818a-68ac6012b58d"

    # async def test_load_video():
    #     await mcp_service.load_video(VIDEO_ID)

    # import asyncio
    # asyncio.run(test_load_video())
