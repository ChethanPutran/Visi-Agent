from src.services.video_processing.app.processors.audio.transcriber import transcribe_audio
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

def test_extract_audio():
    video_path = "data/videos/test_video.mp4"
    res = transcribe_audio(video_path)
    logger.info(f"Transcription Result: {res["text"]}")
    assert res is not None
    