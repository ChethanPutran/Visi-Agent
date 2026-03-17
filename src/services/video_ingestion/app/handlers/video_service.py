import asyncio
import os
import tempfile
import pathlib
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import UploadFile
from src.shared.contracts.video_metadata import VideoMetadata, VideoFormat
from src.shared.storage.storage_service import StorageService
from src.shared.storage.cache_service import VideoCaheService
from src.shared.storage.queue_service import QueueService
from src.services.video_processing.app.processors.text.summarizer import TextSummarizer
from src.services.video_processing.app.processors.vision.frame_analyzer import VideoProcessor
from src.services.video_processing.app.processors.audio.transcriber import transcribe_audio
from src.shared.contracts.video_metadata import VideoMetadata
from src.services.api_gateway.app.schemas.video_schemas import VideoStatus
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus, ProcessingStage
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


class VideoPipeline:
    def __init__(self, mcp_manager) -> None:
        self.mcp_manager = mcp_manager
        self.video_processor = VideoProcessor(mcp_manager)
        self.text_processor = TextSummarizer(mcp_manager)

    async def generate_summary(self,video_id, transcript, frames_data):
        return await self.text_processor.generate_summary(video_id,transcript, frames_data)

    async def process(self, video_path: str, video_id: str,
                      enable_vision_analysis: bool = True) -> Dict[str, Any]:
        """Process video through all stages"""
        logger.info(f"Starting pipeline for {video_id}")

        audio_path = None
        video = None
        error = None

        try:
            audio_path = await self.extract_audio(video_path)

            # 1. Transcribe audio
            logger.info(f"Transcribing audio for {video_id}")

            transcript_task = asyncio.to_thread(transcribe_audio, audio_path)
            
            # 2. Analyze frames (if enabled)
            frames_task = None
            if enable_vision_analysis:
                logger.info(f"Analyzing frames for {video_id}")
                frames_task = asyncio.create_task(
                    self.video_processor.process_video(video_id, video_path)
                )
                
            transcript = await transcript_task
            frames_data = await frames_task if frames_task else None

            # 3. Generate summary
            logger.info(f"Generating summary for {video_id}")
            summary = await self.generate_summary(video_id,transcript, frames_data)

            # 4. Index for search (optional)
            # await index_video_content(video_id, transcript, frames_data)

            result = {
                "video_id": video_id,
                "transcript": transcript,
                "frames": frames_data,
                "summary": summary,
                "success": True
            }

            logger.info(f"Pipeline completed for {video_id}")
            return result
        except Exception as e:
            error = e
        finally:
            if video:
                video.close()

            if audio_path and os.path.exists(audio_path):
                # Clean up temporary audio file
                os.unlink(audio_path)

            if error:
                raise error

    async def extract_audio(self, video_path: str, moviepy=False) -> str:
        """Extract audio from video and return path to audio file"""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_path = tmp_audio.name

        if moviepy:
            from moviepy import VideoFileClip
            video = VideoFileClip(video_path)
            if video.audio is None:
                raise ValueError(f"No audio track found in video : {video_path}")
            video.audio.write_audiofile(audio_path)
            video.close()
            return audio_path
        
        # Much faster + production-grade solution using ffmpeg directly  
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path,
            "-q:a", "0", "-map", "a",
            audio_path, "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.communicate()
        return audio_path
        
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

    def get_video_creation_time(self, video_path: str) -> str:
        """Get video creation time"""
        # Placeholder implementation
        return "2024-01-01T12:00:00"

    def get_video_modification_time(self, video_path: str) -> str:
        """Get video modification time"""
        # Placeholder implementation
        return "2024-01-01T12:30:00"

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

    def get_metadata(self, video_path: str, video_id: str, file: Any) -> VideoMetadata:
        """Extract and return video metadata"""

        fname = pathlib.Path(video_path).name
        # Create initial metadata
        metadata = VideoMetadata(
            id=video_id,
            filename=file.filename or fname,
            original_filename=file.filename or fname,
            file_size=0,
            content_type=file.content_type or "application/octet-stream",
            upload_time=datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            duration=self.get_video_duration(video_path),
            width=self.get_video_width(video_path),
            height=self.get_video_height(video_path),
            fps=self.get_video_fps(video_path),
            format=self.get_video_format(video_path),
            process_start_time=self.get_video_creation_time(video_path),
            process_end_time=self.get_video_modification_time(video_path),
            transcript_word_count=self.get_video_transcript_word_count(
                video_path),
            frame_count=self.get_video_frame_count(video_path),
            processing_time=self.get_video_processing_time(video_path),
            storage_path=video_path
        )
        return metadata


class VideoService:
    def __init__(self, storage_service: StorageService, queue_provider:QueueService,cache_service:VideoCaheService,mcp_service):
        self.storage = storage_service
        self.video_queue = queue_provider
        self.cache = cache_service
        self.mcp_manager = mcp_service
        self.pipeline = VideoPipeline(self.mcp_manager)
        
        # In-memory processing state
        self.processing_table: Dict[str, VideoProcessingStatus] = {}
        self.processing_results = {}

        # Limit GPU tasks to avoid OOM - can be tuned based on GPU capacity and model size
        self.semaphore = asyncio.Semaphore(2)  

    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        return await self.cache.get_video_status(video_id)
            
        # print(f"Getting status for video: {video_id}")
        # print(self.processing_table)
        # print(self.processing_results)
        # # Check in-memory queue first
        # if video_id in self.processing_table:
        #     return self.processing_table[video_id]

        # # Check processing results
        # if video_id in self.processing_results:
        #     return self.processing_results[video_id]

        # return None

    async def set_video_status(self, video_id: str, status: VideoProcessingStatus):
        await self.cache.set_video_status(video_id, status)

    async def remove_video_status(self, video_id: str):
        await self.cache.remove_video_status(video_id, status)

    async def worker(self, worker_id: int):
        logger.info(f"Worker {worker_id} started")

        while True:
            try:
                job = await self.video_queue.pop()
            except Exception as e:
                logger.error(f"Queue error: {e}")
                await asyncio.sleep(2)
                continue

            try:
                
                logger.info(f"Worker {worker_id} processing {job['video_id']}")
                video_metadata = await self.get_video_metadata(job["video_id"])
                
                if not video_metadata:
                    logger.error(f"Worker {worker_id} could not find metadata for video {job['video_id']}")
                    raise ValueError(f"Metadata not found for video {job['video_id']}")
                
                async with self.semaphore:
                    await self.process_video(
                        job["video_id"],
                        video_metadata.storage_path,
                        enable_vision_analysis=job["enable_vision_analysis"]
                    )

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
                
    async def start(self, num_workers: int = 1):
        """Start multiple worker loops"""
        for i in range(num_workers):
            asyncio.create_task(self.worker(i))

        workers = []
        for i in range(1):
            workers.append(asyncio.create_task(self.worker(i)))

        self.workers = workers


    async def add_video_to_queue(self, video_id: str, enable_vision_analysis: bool = True):
        """Add video to processing queue"""
        job = VideoProcessingStatus(
            video_id=video_id,
            status=VideoStatus.QUEUED,
            current_stage=ProcessingStage.NOT_STARTED,
            progress=0.0,
            estimated_completion=None,
            message="Video queued for processing",
            error=None
        )
        self.processing_table[video_id] = job
        # self.video_queue.put_nowait({
        #     "video_id": video_id,
        #     "enable_vision_analysis": enable_vision_analysis
        # })
        await self.video_queue.push({
            "video_id": video_id,
            "enable_vision_analysis": enable_vision_analysis
        })
        logger.debug(f"Added to Queue: {self.processing_table}")

    async def process_video(self, video_id: str, video_path: str,
                            enable_vision_analysis: bool = True,
                            auto_load_mcp: bool = False,
                            save_results: bool = False
                            ) -> Dict[str, Any]:
        """Process a video through the pipeline"""

        logger.debug(f"Initiating processing for video {video_id} at path {video_path}")
        # Try to get status from in-memory table
        # processing_status = self.processing_table.get(video_id, None)
        processing_status = self.processing_table.get(video_id)

        logger.debug(f"Processing Status:: {processing_status}")
        if not processing_status:
            raise ValueError(f"Video {video_id} not found in processing queue")
        try:
            # Update status
            await self._update_status(video_id, processing_status, VideoStatus.PROCESSING)

            logger.info(f"Processing video {video_id}: {video_path}")

            # Run processing pipeline
            result = await self.pipeline.process(
                video_path=video_path,
                video_id=video_id,
                enable_vision_analysis=enable_vision_analysis,

            )

            if save_results:
                # Save results
                await self._save_processing_results(video_id, result)

            # Auto-load to MCP
            if auto_load_mcp and result.get("success", False):
                mcp_result = await self.mcp_manager.load_video(video_id)
                result["mcp_loaded"] = mcp_result["success"]
                if mcp_result["success"]:
                    logger.info(f"Auto-loaded video {video_id} to MCP")

            # Update status
            await self._update_status(video_id, processing_status, VideoStatus.COMPLETED)

            logger.debug(f"Video {video_id} processed successfully")
            return result

        except Exception as e:
            logger.error(f"Error processing video {video_id}: {str(e)}")
            await self._update_status(video_id, processing_status, VideoStatus.FAILED, data={"error": str(e)})
            raise

    async def process_video_batch(self, video_ids: List[str], video_paths: List[str],
                                  enable_vision_analysis: bool = True) -> List[Dict[str, Any]]:
        """Process a batch of videos through the pipeline"""
        results = []
        for video_id, video_path in zip(video_ids, video_paths):
            res = await self.process_video(video_id, video_path, enable_vision_analysis)
            results.append(res)
        return results

    async def upload_batch_videos(self, files: List[UploadFile]) -> List[VideoMetadata]:
        """Upload and queue a batch of videos for processing"""
        metadata_list = []
        for file in files:
            metadata = await self.upload_video(file)
            metadata_list.append(metadata)
        return metadata_list

    async def upload_video(self, file: UploadFile) -> VideoMetadata:
        """Upload and queue a video for processing"""
        video_id = str(uuid.uuid4())

        try:
            # Save video file
            video_path = await self.storage.save_video(file, video_id)
            metadata = self.pipeline.get_metadata(video_path, video_id, file)

            # Store metadata
            await self.storage.save_video_metadata(metadata)

            # Store metadata
            await self.cache.set(f"video:{video_id}:metadata", json.dumps(metadata.model_dump()))
            
            return metadata

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise

    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""
        metadata = await self.cache.get(f"video:{video_id}:metadata")
        if metadata:
            return metadata
        metadata = await self.storage.get_video_metadata(video_id)
        return metadata

    async def get_video_transcript(self, video_id: str, format: str = "json") -> Optional[Any]:
        """Get video transcript"""
        try:
            transcript = await self.storage.get_transcript(video_id, format)
            return transcript
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            return None

    async def get_video_summary(self, video_id: str) -> Optional[str]:
        """Get video summary"""
        try:
            summary = await self.storage.get_summary(video_id)
            return summary
        except Exception as e:
            logger.error(f"Error getting summary: {str(e)}")
            return None

    async def list_videos(
            self,
            page,
            limit,
            status
        ):
        return {}
    # async def list_videos(self, page: int = 1, limit: int = 20,
    #                       status: Optional[str] = None) -> tuple[List[Dict], int]:
    #     """List videos with pagination"""
    #     # In production, use database
    #     # For now, return from cache

    #     self.storage.list_all_videos()

    #     # Get from processing queue
    #     for item in self.processing_table.values():
    #         all_videos.append(item)

    #     # Get from results
    #     for item in self.processing_results.values():
    #         all_videos.append(item)

    #     # Filter by status
    #     if status:
    #         all_videos = [v for v in all_videos if v.get("status") == status]

    #     # Paginate
    #     start_idx = (page - 1) * limit
    #     end_idx = start_idx + limit
    #     paginated = all_videos[start_idx:end_idx]

    #     return paginated, len(all_videos)

    async def delete_video(self, video_id: str) -> bool:
        """Delete video and all associated data"""
        try:
            # Delete from storage
            success = await self.storage.delete_video_data(video_id)

            # Delete from cache
            await self.cache.delete(f"video:{video_id}:metadata")
            await self.cache.delete(f"video:{video_id}:status")
            await self.cache.delete(f"video:{video_id}:results")

            # Delete from in-memory
            self.processing_table.pop(video_id, None)
            self.processing_results.pop(video_id, None)

            logger.info(f"Deleted video {video_id}")
            return success

        except Exception as e:
            logger.error(f"Error deleting video {video_id}: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        return {
            "healthy": True,
            "service": "video_service",
            "queue_size": len(self.processing_table),
            "processed_count": len(self.processing_results),
            "timestamp": datetime.now()
        }

    # Private methods
    async def _update_status(self, video_id: str, status_obj: VideoProcessingStatus, status: VideoStatus,
                             data: Optional[Dict] = None):
        """Update video processing status"""
        if not status_obj:
            return
        # Update status object
        status_obj.status = status
        status_obj.updated_at = datetime.now()

        status_obj.current_stage = data.get(
            "current_stage") if data and "current_stage" in data else status_obj.current_stage
        status_obj.progress = data.get(
            "progress", 0) if data and "progress" in data else status_obj.progress
        status_obj.estimated_completion = data.get(
            "estimated_completion") if data and "estimated_completion" in data else status_obj.estimated_completion
        status_obj.message = data.get(
            "message") if data and "message" in data else status_obj.message
        status_obj.error = data.get(
            "error") if data and "error" in data else status_obj.error

        if data:
            status_obj.updated_at = datetime.now()

        # Update in-memory
        if status == VideoStatus.COMPLETED or status == VideoStatus.FAILED:
            # Build final status
            status_obj.progress = 100.0
            self.processing_results[video_id] = status_obj
            status_obj.message = "Processing completed" if status == VideoStatus.COMPLETED else "Processing failed"
            status_obj.error = None if status == VideoStatus.COMPLETED else status_obj.error
            status_obj.estimated_completion = datetime.now()
            self.remove_video_status(video_id)
        else:
            self.set_video_status(video_id, status_obj)

        # Update cache
        await self.cache.set(f"video:{video_id}:status", json.dumps(status))

    async def _save_processing_results(self, video_id: str, result: Dict[str, Any]):
        print("Saving processing results for video:", video_id, result)
        """Save processing results to storage"""
        # Save transcript
        if "transcript" in result:
            await self.storage.save_transcript(video_id, result["transcript"])

        # Save summary
        if "summary" in result:
            await self.storage.save_summary(video_id, result["summary"])

        # Save frames data
        if "frames" in result:
            await self.storage.save_frames(video_id, result["frames"])

        # Cache results
        await self.cache.set(f"video:{video_id}:results", json.dumps(result))
