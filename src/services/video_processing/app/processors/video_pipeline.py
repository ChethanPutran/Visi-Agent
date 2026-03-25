
import asyncio
import os
import tempfile
import pathlib
from PIL import Image
import cv2
from typing import Dict, Any, List
from datetime import datetime
from typing import Dict,Any, List
# from sentence_transformers import MultiModalBERT # Or CLIP
import torch
from transformers import CLIPProcessor, CLIPModel
from src.services.llm_service.app.llm_service import LLMService
from src.shared.contracts.video_metadata import VideoMetadata, VideoFormat
from src.services.video_processing.app.processors.text.summarizer import TextSummarizer
from .vision.frame_analyzer import VideoProcessor
from .audio.transcriber import Transcriber
from src.shared.contracts.video_metadata import VideoMetadata
from src.services.video_processing.app.contracts.schemas import ProcessingStage
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class VideoPipeline:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service
        self.video_processor = VideoProcessor(llm_service)
        self.text_processor = TextSummarizer(llm_service)
        self.transcriber = Transcriber()
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")

    async def generate_summary(self, video_id, transcript, frames_data):
        return await self.text_processor.generate_summary(video_id, transcript, frames_data)

    def process_video_to_store(self, paired_data: List[Dict]):
        """
        paired_data: Output from VideoProcessor.get_frames_for_segments
        """
        entries = []
        
        with torch.no_grad():
            for pair in paired_data:
                # 1. Embed the Text Caption
                text_inputs = self.clip_processor(text=[pair['text']], return_tensors="pt", padding=True).to(self.device)
                text_embeds = self.clip_model.get_text_features(**text_inputs)
                text_embeds /= text_embeds.norm(p=2, dim=-1, keepdim=True)
                
                entries.append({
                    "values": text_embeds.cpu().numpy().tolist()[0],
                    "metadata": {
                        "text": pair['text'],
                        "start": pair['start'],
                        "type": "audio_caption"
                    }
                })

                # 2. Embed the representative frames in the batch
                for f_data in pair['frame_batch']:
                    # Convert OpenCV (BGR) to PIL (RGB) for CLIP
                    pil_img = Image.fromarray(cv2.cvtColor(f_data['image'], cv2.COLOR_BGR2RGB))
                    
                    img_inputs = self.clip_processor(images=pil_img, return_tensors="pt").to(self.device)
                    img_embeds = self.clip_model.get_image_features(**img_inputs)
                    img_embeds /= img_embeds.norm(p=2, dim=-1, keepdim=True)

                    entries.append({
                        "values": img_embeds.cpu().numpy().tolist()[0],
                        "metadata": {
                            "text": pair['text'], # Link to transcript text
                            "timestamp": f_data['timestamp'],
                            "type": "visual_frame"
                        }
                    })
        return entries
    

    async def process(self, video_path: str, video_id: str, enable_vision_analysis: bool = True, callback=None) -> Dict[str, Any]:
        """Process video through all stages"""
        logger.info(f"Starting pipeline for {video_id}")

        audio_path = None
        error = None
        result = {}

        try:
            # --- STAGE: AUDIO ---
            if callback:
                await callback(ProcessingStage.AUDIO_EXTRACTION, 0.1, "Extracting audio...")
                logger.debug(f"Updating status for {video_id}: {ProcessingStage.AUDIO_EXTRACTION} | Data: 0.1")
            audio_path = await self.extract_audio(video_path)

            # --- STAGE: START CONCURRENT TASKS ---
            if callback:
                await callback(ProcessingStage.TRANSCRIPTION, 0.3, "Analyzing media content...")
                logger.debug(f"Updating status for {video_id}: {ProcessingStage.TRANSCRIPTION} | Data: 0.3")


            # Run transcription in thread (since it's likely CPU bound/wrapper)
            transcript_task = asyncio.to_thread(
                self.transcriber.transcribe_audio, audio_path)

            # Wait for transcription first
            transcript = await transcript_task

            frames_data = None
            embeddings = None
            summary = None
            
            if enable_vision_analysis:
                # Start vision analysis in background
                frames_task = asyncio.create_task(
                    self.video_processor.process_video(video_id, video_path)
                )

                # Update progress after transcription is done
                if callback:
                    await callback(ProcessingStage.VISION_ANALYSIS, 0.6, "Finalizing visual analysis...")
                    logger.debug(f"Updating status for {video_id}: {ProcessingStage.VISION_ANALYSIS} | Data: 0.6")

                # Now wait for frames (it might already be done)
                frames_data = await frames_task if frames_task else None

                # --- STAGE: SUMMARY ---
                if callback:
                    await callback(ProcessingStage.SUMMARIZATION, 0.8, "Generating AI summary...")
                    logger.debug(f"Updating status for {video_id}: {ProcessingStage.SUMMARIZATION} | Data: 0.8")

                summary = await self.generate_summary(video_id, transcript, frames_data)
            else:
                paired_data = self.video_processor.get_frames_for_segments(video_path, transcript['segments'])
                embeddings = self.process_video_to_store(paired_data)


            if callback:
                await callback(ProcessingStage.COMPLETED, 1.0, "Processing complete!")
                logger.debug(f"Updating status for {video_id}: {ProcessingStage.COMPLETED} | Data: 1.0")


            result = {
                "video_id": video_id,
                "transcript": transcript,
                "frames": frames_data,
                "embeddings": embeddings,
                "summary": summary,
                "success": True
            }

        except Exception as e:
            logger.error(f"Pipeline failed for {video_id}: {str(e)}")
            error = e
            # If you need to update DB on failure:
            if callback:
                await callback(ProcessingStage.FAILED, 0.0, f"Error: {str(e)}")
                logger.debug(f"Updating status for {video_id}: {ProcessingStage.FAILED} | Data: 0.0")

        finally:
            # Cleanup
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except Exception as e:
                    logger.error(f"Failed to delete temp audio: {e}")

            if error:
                raise error  # Re-raise after cleanup

            return result

    async def extract_audio(self, video_path: str, moviepy=False) -> str:
        """Extract audio from video with strict process cleanup"""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_path = tmp_audio.name

        # Faster + production-grade solution using ffmpeg
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path,
            "-q:a", "0", "-map", "a",
            audio_path, "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.communicate()
        except asyncio.CancelledError:
            # Check if the process is still running
            if process.returncode is None:
                try:
                    logger.warning(
                        f"Killing FFmpeg process for {video_path} due to cancellation")
                    process.kill()
                    # to clear the zombie from the OS process table
                    await process.wait()
                except ProcessLookupError:
                    # Process already died on its own
                    pass
            raise  # Re-raise to let the worker exit

        return audio_path

    async def extract_thumbnail(self, video_path: str, thumbnail_path: str):
        """Extract a frame from the video to use as a thumbnail"""
        # FFmpeg command: -ss 1 (at 1 second), -vframes 1 (take one frame)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path,
            "-ss", "00:00:01.000", "-vframes", "1",
            thumbnail_path, "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.communicate()
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            logger.error(f"Thumbnail extraction failed: {e}")

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds"""
        # Placeholder implementation
        return 120.0

    def get_video_width(self, video_path: str) -> int:
        """Get video width in pixels"""
        # Placeholder implementation
        return 1920

    def get_video_height(self, video_path: str) -> int:
        """Get video height in pixels"""
        # Placeholder implementation
        return 1080

    def get_video_fps(self, video_path: str) -> float:
        """Get video frames per second"""
        # Placeholder implementation
        return 30.0

    def get_video_creation_time(self, video_path: str) -> datetime:
        """Get video creation time"""
        # Placeholder implementation
        return datetime.now()

    def get_video_modification_time(self, video_path: str) -> datetime:
        """Get video modification time"""
        # Placeholder implementation
        return datetime.now()

    def get_video_transcript_word_count(self, video_path: str) -> int:
        """Get word count of the transcript"""
        # Placeholder implementation
        return 1500

    def get_video_frame_count(self, video_path: str) -> int:
        """Get total number of frames analyzed"""
        # Placeholder implementation
        return 3600

    def get_video_processing_time(self, video_path: str) -> float:
        """Get total processing time in seconds"""
        # Placeholder implementation
        return 300.0

    def get_video_format(self, video_path: str) -> VideoFormat:
        """Get video format (e.g., mp4, avi)"""
        # Placeholder implementation
        return VideoFormat.MP4

    async def get_metadata(self, video_path: str, video_id: str, file: Any) -> VideoMetadata:
        """Extract and return video metadata"""

        fname = pathlib.Path(video_path).name
        thm_path = os.path.join("thumbnails", f"{video_id}.jpg")

        # Extract thumbnail
        await self.extract_thumbnail(video_path,  os.path.join(os.path.dirname(video_path), "..", thm_path))

        # Create initial metadata
        metadata = VideoMetadata(
            id=video_id,
            filename=file.filename or fname,
            original_filename=file.filename or fname,
            file_size=0,
            content_type=file.content_type or "application/octet-stream",
            upload_time=datetime.now(),
            duration=self.get_video_duration(video_path),
            width=self.get_video_width(video_path),
            height=self.get_video_height(video_path),
            fps=self.get_video_fps(video_path),
            format=self.get_video_format(video_path),
            thumbnail_path=thm_path,
            process_start_time=None,
            process_end_time=None,
            transcript_word_count=None,
            frame_count=None,
            processing_time=None,
            storage_path=video_path
        )
        return metadata

