"""
Audio transcription using Whisper
"""
import whisper
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from typing import Any, Dict

logger = get_logger(__name__)

# Load model once
_model = None


def get_model():
    global _model
    if _model is None:
        device = "cpu"

        logger.info(f"Loading Whisper model on {device}")

        _model = whisper.load_model(
            settings.WHISPER_MODEL,
            device=device
        )
    return _model


def transcribe_audio(video_path: str) -> Dict[str, Any]:
    """Transcribe audio from video"""
    # return {
    #     "text": "Transcribing audio..."
    # }
    
    try:
        model = get_model()
        result = model.transcribe(
            video_path,
            fp16=False  # for CPU
        )
        return result
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise
