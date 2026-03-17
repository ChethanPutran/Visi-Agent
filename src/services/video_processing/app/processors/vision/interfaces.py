from typing import Dict, List, Protocol


class FrameAnalysisProvider(Protocol):
    def analyze_frames_batch(self, video_id: str, frame_buffer: List[Dict]) -> List[Dict]:
        """Analyze a batch of frames and return enriched frame data."""
