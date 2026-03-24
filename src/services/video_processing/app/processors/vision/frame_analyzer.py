import base64
from typing import Dict, List
import cv2
import numpy as np
from src.services.llm_service.app.mcp_service import MCPService
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
    def __init__(self, mcp_manager: MCPService = None) -> None:
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
    
    def extract_frames_from_caption_segments(self, video_id:str, video_path: str, segments: List, use_llm: bool):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames_data = []

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
    
    async def extract_clips(self, video_path: str, from_:str,to_:str) -> str:
        """Extract audio from video with strict process cleanup"""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_audio:
            clip_path = tmp_audio.name

        # Faster + production-grade solution using ffmpeg
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path,
            "-ss", from_,"-to",to_, "-c", "copy",
            clip_path, "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.communicate()
        except asyncio.CancelledError:
            # Check if the process is still running
            if process.returncode is None:
                try:
                    logger.warning(f"Killing FFmpeg process for {video_path} due to cancellation")
                    process.kill()
                    # to clear the zombie from the OS process table
                    await process.wait() 
                except ProcessLookupError:
                    # Process already died on its own
                    pass
            raise # Re-raise to let the worker exit
        
        return clip_path


    async def extract_clips_from_caption_segments(self, video_id:str, video_path: str, segments: List, use_llm: bool):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        clips_data = []

        for segment in segments:
            start_time = segment['start']
            end_time = segment['end']

            clip_path = await self.extract_clips(video_path,start_time,end_time)

            clips_data.append(
                {
                    'clip': clip_path,
                    'start':start_time,
                    'end':end_time
                }
            )
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


    async def process_video(self, video_id, video_path: str, batch_size: int = 5, use_llm: bool = True) -> List[Dict[str,str]]:
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
