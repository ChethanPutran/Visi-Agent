from src.services.video_processing.app.processors.vision.frame_analyzer import VideoProcessor
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class TestMCPManager:
    def analyze_frames_batch(self,video_id,frame_batch):
        transcript_segments=[]
        frames_data =[]
        summary = "This is test summary"
        return transcript_segments, frames_data, summary

def test_extract_video():
    video_path = "data/videos/test_video.mp4"

    test_mcp_man = TestMCPManager()
    vp = VideoProcessor(test_mcp_man)
    video_id = 1

    try:
        transcript_segments, frames_data, summary = vp.process_video(video_id,
            video_path, 
            batch_size=3     # Adjust based on your needs
        )
        # Print summary
        print("\n" + "="*50)
        print("VIDEO SUMMARY")
        print("="*50)
        print(summary)
        print("="*50)
        
        print(f"\nTranscript segments: {len(transcript_segments)}")
        print(f"Key frames analyzed: {len(frames_data)}")
        
    except Exception as e:
        print(f"Error processing video: {e}")
