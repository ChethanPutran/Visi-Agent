"""
Audio transcription using Whisper
"""
from typing_extensions import Self

import torch
import whisper
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from typing import Any, Dict
import threading

logger = get_logger(__name__)

class TranscriptionError(Exception):
    """Custom exception for transcription errors"""
    pass

class ModelLoadError(Exception):
    """Custom exception for model loading errors"""
    pass

class Transcriber:
    """Class for transcribing audio from video using Whisper"""

    _model = None
    _model_lock = threading.Lock()

    def __init__(self):
        pass

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super(Transcriber, cls).__new__(cls)
        return cls._instance

    def get_model(self) -> whisper.Whisper:
        """Load and return the Whisper model, ensuring it's only loaded once"""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"Loading Whisper model on {device}")

                    self._model = whisper.load_model(
                        settings.WHISPER_MODEL,
                        device=device
                    )
        return self._model

    def transcribe_audio(self, video_path: str) -> Dict[str, Any]:
        """Transcribe audio from video"""
        try:
            model = self.get_model()

            fp16 = torch.cuda.is_available()

            result = model.transcribe(
                video_path,
                fp16=fp16
            )

            return result

        except Exception:
            logger.exception("Transcription error")
            raise
        
if __name__ == "__main__":
    transcriber = Transcriber()
    data = transcriber.transcribe_audio("data/videos/test_video.mp4")
    print(data)