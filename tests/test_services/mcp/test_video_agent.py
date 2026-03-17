from src.services.llm_service.app.agent.core.video_agent import VideoAnalyticsAgent 
from src.services.video_processing.app.processors.vision.frame_analyzer import VideoProcessor 
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


def test_video_agent():
    video_path = "data/videos/test_video.mp4"
    video_id = "1"

    vp = VideoProcessor()
    data = vp.process_video(video_id,video_path,1,False)
    
    # print(data)
    # agent = VideoAnalyticsAgent()
    # agent.analyze_frames_batch()
    logger.info(f"Transcription Result: {data[0]}")
    # assert res is not None