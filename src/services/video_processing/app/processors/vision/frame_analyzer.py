import base64
from typing import Any, Dict, List
import cv2
import numpy as np
from src.services.llm_service.app.llm_service import LLMService
from src.shared.logging.logger import get_logger
import tempfile
import asyncio 

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
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def _encode_to_base64(self, frame):
        """Convert a frame to base64 for GPT-4 Vision API"""
        # Using a quality of 80 is usually the sweet spot for LLMs
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return base64.b64encode(buffer).decode('utf-8')

    def _check_llm(self):
        assert self.llm_service is not None, "LLM Service is not set!"

    # def analyze_frames_batch(self, video_id, frame_batch):
    #     self._check_llm()
    #     return self.llm_service.analyze_frames_batch(video_id, frame_batch)
    
    def get_frames_for_segments(self, video_path: str, segments: List[Dict[str, Any]], sample_rate: float = 1.0):
        """
        Extracts a batch of frames for each caption segment.
        sample_rate: seconds between frame captures within a segment.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        results = []

        for segment in segments:
            start_s, end_s = segment['start'], segment['end']
            frames_in_segment = []
            
            # Jump to start of segment
            cap.set(cv2.CAP_PROP_POS_MSEC, start_s * 1000)
            
            # Calculate how many frames to skip to hit our sample rate
            skip_frames = int(fps * sample_rate)
            current_ms = start_s * 1000
            
            while current_ms < (end_s * 1000):
                ret, frame = cap.read()
                if not ret: break
                
                # Resize for CLIP/LLM (CLIP usually takes 224x224 or similar)
                resized = cv2.resize(frame, (512, 512), interpolation=cv2.INTER_AREA)
                
                frames_in_segment.append({
                    "timestamp": current_ms / 1000.0,
                    "image": resized, # Keep raw for CLIP
                    "base64": self._encode_to_base64(resized) # For LLM Vision
                })
                
                # Skip to next sample point
                current_ms += (sample_rate * 1000)
                cap.set(cv2.CAP_PROP_POS_MSEC, current_ms)

            results.append({
                "start": start_s,
                "end": end_s,
                "text": segment.get('text', ''),
                "frame_batch": frames_in_segment
            })

        cap.release()
        return results

 
    def extract_frames_from_caption_segments(self, video_id: str, video_path: str, segments: List, use_llm: bool):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames_data = []
        
        # We sample one frame every X seconds (e.g., every 2 seconds)
        sample_rate_seconds = 2
        sample_interval = int(fps * sample_rate_seconds)
        TARGET_WIDTH = 512

        for segment in segments:
            start_time = segment['start']
            end_time = segment['end']
            
            # Set video position to the start of the segment
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            frame_batch = []
            # Calculate how many frames to read based on segment duration
            duration_frames = int((end_time - start_time) * fps)
            
            for i in range(0, duration_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_POS_FRAMES) + sample_interval)
                ret, frame = cap.read()
                if not ret:
                    break

                # --- RESIZING LOGIC ---
                height, width = frame.shape[:2]
                aspect_ratio = width / height
                new_height = int(TARGET_WIDTH / aspect_ratio)
                
                resized_frame = cv2.resize(frame, (TARGET_WIDTH, new_height), interpolation=cv2.INTER_AREA)
                # ----------------------
                    
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                base64_image = self.encode_image_to_base64(resized_frame)
                
                frame_batch.append({
                    "timestamp": round(timestamp, 2),
                    "base64_image": base64_image
                })

            description = ''
            if use_llm and frame_batch:
                description = self.analyze_frames_batch(video_id, frame_batch)

            frames_data.append({
                'time_range': f"{start_time:.2f}-{end_time:.2f}",
                'frames': frame_batch if not use_llm else [], # Keep memory low if LLM is used
                'caption': segment.get('text', ''),
                'description': description,
                'start': start_time,
                'end': end_time,
            })

        cap.release()
        return frames_data

    async def extract_clips(self, video_path: str, from_: float, to_: float) -> str:
        """Extract a sub-clip from video using FFmpeg"""
        # Ensure we are passing strings to FFmpeg
        start_ts = str(from_)
        end_ts = str(to_)
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_clip:
            clip_path = tmp_clip.name

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-ss", start_ts, "-to", end_ts, "-i", video_path,
            "-c", "copy", "-y", clip_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.wait()
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
        
        return clip_path
    
    async def extract_clips_from_caption_segments(self, video_id: str, video_path: str, segments: List):
        """
        Iterates through segments and calls the async FFmpeg extractor.
        Note: Removed cv2 dependency here as FFmpeg handles the timing.
        """
        clips_data = []

        # Using asyncio.gather could parallelize this, but FFmpeg is CPU intensive.
        # We'll stick to sequential processing to avoid crashing the CPU/Disk IO.
        for segment in segments:
            start_time = segment.get('start')
            end_time = segment.get('end')
            
            # Ensure we have valid timestamps
            if start_time is None or end_time is None:
                continue

            # extract_clips is your FFmpeg-based helper
            clip_path = await self.extract_clips(video_path, start_time, end_time)

            clips_data.append({
                'video_id': video_id,
                'clip_path': clip_path,
                'start': start_time,
                'end': end_time,
                'text': segment.get('text', '')
            })

        return clips_data





        count = 0
        frame_batch = []
        timestamp = 0
        segment_id = 0
        cur_segment = segments[0]
        end_time = cur_segment['end']


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

            if timestamp >= end_time:
                description = ''
                if use_llm:
                    description = self.analyze_frames_batch(
                        video_id, frame_batch)
                    time_range = f"{frame_batch[0]['timestamp']:.2f}-{frame_batch[-1]['timestamp']:.2f}"
                    frames_data.append({"time_range":time_range,
                                        "description":description,
                                        })
                    frame_batch = []
                    break

                # Store the processed segment
                frames_data.append({
                    'frames': frame_batch,
                    'caption':cur_segment['text'],
                    'description':description,
                    'start':cur_segment['start'],
                    'end':cur_segment['end'],
                    'tokens':cur_segment['tokens'],
                })
                
                # Update current segment
                frame_batch = []
                segment_id += 1
                cur_segment = segments[segment_id]
                end_time = cur_segment['end']

        if frame_batch:
            if use_llm:
                # Process any remaining frames in the batch
                description = self.analyze_frames_batch(
                    video_id, frame_batch)
            else:
                description = ''

            # Store the processed segment
            frames_data.append({
                'frames': frame_batch,
                'caption':cur_segment['text'],
                'description':description,
                'start':cur_segment['start'],
                'end':cur_segment['end'],
                'tokens':cur_segment['tokens'],
            })
            
            # Update current segment
            frame_batch = []

        cap.release() 

        return frames_data    

    async def process_video(self, video_id, video_path: str, batch_size: int = 5, use_llm: bool = False, store_frames: bool = False) -> List[Dict[str,str]]:
        """
        Process a video file: extract audio, transcribe, analyze frames, and generate summary.

        Args:
            video_path: Path to the video file
            use_gpt4v: Whether to use GPT-4 Vision for frame analysis
            batch_size: Number of frames to send in a single API call
            store_frames: Whether to store the actual frame images

        Returns:
            tuple: (transcript_segments, frames_data, summary)
        """
        # if use_llm:
        #     self._check_mcp()

            
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
                # Process batch when it reaches batch_size
                if len(frame_batch) >= batch_size:
                    if use_llm:
                        description = self.analyze_frames_batch(video_id, frame_batch)
                    else:
                        description = ''

                    frames_data.append(
                        {
                        "start_time":frame_batch[0]['timestamp'],
                            "end_time":frame_batch[-1]['timestamp'],
                            "time_range": f"{frame_batch[0]['timestamp']:.2f}-{frame_batch[-1]['timestamp']:.2f}",
                            "description": description,
                            "frames": frame_batch if store_frames else []
                        })
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

            frames_data.append(
                {
                "start_time":frame_batch[0]['timestamp'],
                    "end_time":frame_batch[-1]['timestamp'],
                    "time_range": f"{frame_batch[0]['timestamp']:.2f}-{frame_batch[-1]['timestamp']:.2f}",
                    "description": description,
                    "frames": frame_batch if store_frames else []   
                })
        cap.release()

        # Sort frames by timestamp
        # frames_data.sort(key=lambda x: x['time_range'])

        return frames_data


# if __name__ == "__main__":
#     from src.shared.config.settings import LLMModel, StorageType
#     from src.shared.storage.factories.blob_storage_service import StorageService

#     # Example usage
#     se = StorageService(StorageType.LOCAL)
#     llm_service = MCPService(se, LLMModel.GEMINI)
#     video_processor = VideoProcessor(llm_service)
#     video_path = "path_to_your_video.mp4"

#     VIDEO_ID = "8bf5d8af-aa6d-4ae1-818a-68ac6012b58d"
    
#     # Run the video processing in an async context
#     async def main():
#         frames_data = await video_processor.process_video(VIDEO_ID, video_path, use_llm=True)
#         print(frames_data)

#     asyncio.run(main())