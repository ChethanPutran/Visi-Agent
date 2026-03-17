import base64
from typing import Dict, List
import cv2
import numpy as np
from src.services.llm_service.app.mcp_service import MCPManager
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


class FrameBatch:
    def __init__(self, timestamp,base64_image,description) -> None:
        self._timestamp = timestamp
        self._base64_image = base64_image
        self._description = description

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def base64_image(self):
        return self._base64_image

    @property
    def description(self):
        return self._description


class VideoProcessor:
    def __init__(self, mcp_manager: MCPManager = None) -> None:
        self.mcp_manager = mcp_manager

    def encode_image_to_base64(self, frame: np.ndarray) -> str:
        """Convert a frame to base64 for GPT-4 Vision API"""
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')

    def _check_mcp(self):
        assert self.mcp_manager is not None, "MCP Manager is not set!"

    def analyze_frames_batch(self, video_id, frame_batch):
        self._check_mcp()
        return self.mcp_manager.analyze_frames_batch(video_id, frame_batch)

    def process_video(self, video_id, video_path: str, batch_size: int = 5, use_llm: bool = True) -> List[Dict[str,str]]:
        """
        Process a video file: extract audio, transcribe, analyze frames, and generate summary.

        Args:
            video_path: Path to the video file
            use_gpt4v: Whether to use GPT-4 Vision for frame analysis
            batch_size: Number of frames to send in a single API call

        Returns:
            tuple: (transcript_segments, frames_data, summary)
        """
        if use_llm:
            self._check_mcp()
        logger.info(f"Processing video: {video_path}")

        # Extract Key Frames (every 2 seconds)
        logger.info("Extracting key frames...")
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames_data = []

        count = 0
        frame_batch = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if count % (2 * int(fps)) == 0:
                timestamp = count / fps

                # Prepare frame for batch processing
                base64_image = self.encode_image_to_base64(frame)
                frame_batch.append({
                    "timestamp": timestamp,
                    "base64_image": base64_image
                })

                # Extract the information in the video chunk using llm if asked
                if use_llm:
                    # Process batch when it reaches batch_size
                    if len(frame_batch) >= batch_size:
                        description = self.analyze_frames_batch(
                            video_id, frame_batch)
                        time_range = f"{frame_batch[0]['timestamp']:.2f}-{frame_batch[-1]['timestamp']:.2f}"
                        frames_data.append({"time_range":time_range,"description":description})
                        frame_batch = []
                        break

            count += 1

        if frame_batch:
            if use_llm:
                # Process any remaining frames in the batch
                description = self.analyze_frames_batch(
                    video_id, frame_batch)
            else:
                description = ''
            time_range = f"{frame_batch[0]['timestamp']}-{frame_batch[-1]['timestamp']}"
            frames_data.append({"time_range":time_range,"description":description})

        cap.release()

        # Sort frames by timestamp
        # frames_data.sort(key=lambda x: x['time_range'])

        return frames_data
