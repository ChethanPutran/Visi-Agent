import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from src.services.llm_service.app.agent.core.video_agent import VideoAnalyticsAgent
from src.services.llm_service.app.agent.tools.video_search import initialize_video_search
from src.shared.storage.storage_service import StorageService
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


class MCPManager:
    """Manages MCP video sessions with persistence"""
    _instance: Optional["MCPManager"] = None

    def __init__(self, storage_service: StorageService, model: str):
        if self._initialized:
            return

        self._model = model
        self.storage_service = storage_service
        self.sessions: Dict[str, VideoSession] = {}
        self.agent_pool: Dict[str, VideoAnalyticsAgent] = {}
        self._initialized = True
        logger.info(f"Using model: {model}")
        
    def __new__(cls, storage_service: StorageService, model: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance


    @property
    def model(self) -> str:
        return self._model
    
    def _get_agent(self,video_id):
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
            transcript = await self.storage_service.get_transcript(video_id, "json")
            frames_data = await self.storage_service.get_frames_data(video_id)
            metadata = await self.storage_service.get_video_metadata(video_id)

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

          
            agent = self._get_agent(video_id)

            # Initialize search with processed data
            initialize_video_search(
                transcript_segments=transcript.get("segments", []),
                frames_data=frames_data.get("frames", []),
                video_path=metadata.storage_path
            )

            # Create session
            session = VideoSession(
                video_id=video_id,
                agent=agent,
                metadata=metadata,
                loaded_at=datetime.now()
            )

            # Update agent state
            agent.video_loaded = True
            # Convert VideoMetadata to dict using vars()
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
            
            # Enhance response
            response.update({
                "video_id": video_id,
                "query_count": session.query_count,
                "loaded_at": session.loaded_at.isoformat()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "video_id": video_id
            }
    
    def generate_summary(self, video_id, transcript_segments,frames_data):
        agent = self._get_agent(video_id)
        return agent.generate_video_summary(transcript_segments,frames_data)
    
    async def get_summary(self, video_id: str) -> Dict[str, Any]:
        """Get video summary via MCP"""
        if video_id not in self.sessions:
            load_result = await self.load_video(video_id)
            if not load_result["success"]:
                return load_result
        
        session = self.sessions[video_id]
        
        try:
            response = await session.agent.get_video_summary()
            response["video_id"] = video_id
            return response
            
        except Exception as e:
            logger.error(f"Failed to get summary for {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_session_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        if video_id in self.sessions:
            session = self.sessions[video_id]
            return {
                "video_id": session.video_id,
                "loaded_at": session.loaded_at.isoformat(),
                "query_count": session.query_count,
                "last_query_time": session.last_query_time.isoformat() if session.last_query_time else None,
                "metadata": session.metadata
            }
        return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        return [
            session_info
            for video_id in self.sessions.keys()
            if (session_info := self.get_session_info(video_id)) is not None
        ]
    
    def unload_video(self, video_id: str) -> bool:
        """Unload a video from memory"""
        if video_id in self.sessions:
            del self.sessions[video_id]
            logger.info(f"Unloaded video {video_id} from MCP")
            return True
        return False
    
    def analyze_frames_batch(self, video_id,frame_buffer):
        return "This is a placeholder response for frame analysis for video_id: {video_id}"
        agent = self._get_agent(video_id)
        response = agent.analyze_frames_batch(frame_buffer)
        return response
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        return {
            "status": "healthy",
            "active_sessions": len(self.sessions),
            "agent_pool_size": len(self.agent_pool),
            "timestamp": datetime.now().isoformat()
        }
