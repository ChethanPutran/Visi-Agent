"""
Audio transcription using Whisper
"""
import torch
import whisper
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger
from typing import Any, Dict

logger = get_logger(__name__)

# Load model once
_model = None

import whisper
import torch
import threading
from typing import Any, Dict

from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

_model = None
_model_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading Whisper model on {device}")

                _model = whisper.load_model(
                    settings.WHISPER_MODEL,
                    device=device
                )
    return _model


def transcribe_audio(video_path: str) -> Dict[str, Any]:
    """Transcribe audio from video"""
    try:
        model = get_model()

        fp16 = torch.cuda.is_available()

        result = model.transcribe(
            video_path,
            fp16=fp16
        )

        return result

    except Exception:
        logger.exception("Transcription error")
        raise
    
