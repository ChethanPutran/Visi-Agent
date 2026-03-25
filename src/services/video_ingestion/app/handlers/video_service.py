import asyncio
import os
import tempfile
import pathlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from fastapi import UploadFile
from src.services.llm_service.app.mcp_service import MCPService
from src.shared.contracts.video_metadata import VideoMetadata, VideoFormat
from src.shared.storage.repository.video_repository import VideoRepository
from src.shared.storage.providers.cache.redis_cache import VideoCacheService
from src.shared.storage.queue_service import QueueService
from src.services.video_processing.app.processors.text.summarizer import TextSummarizer
from src.services.video_processing.app.processors.vision.frame_analyzer import VideoProcessor
from src.services.video_processing.app.processors.audio.transcriber import Transcriber
from src.shared.contracts.video_metadata import VideoMetadata
from src.services.api_gateway.app.schemas.video_schemas import VideoStatus
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus, ProcessingStage
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


class VideoPipeline:
    def __init__(self, mcp_manager: MCPService) -> None:

        self.mcp_manager = mcp_manager
        self.video_processor = VideoProcessor(mcp_manager)
        self.text_processor = TextSummarizer(mcp_manager)
        self.transcriber = Transcriber()

    async def generate_summary(self, video_id, transcript, frames_data):
        return await self.text_processor.generate_summary(video_id, transcript, frames_data)

    async def process(self, video_path: str, video_id: str,
                      enable_vision_analysis: bool = True, callback=None) -> Dict[str, Any]:
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

            frames_task = None
            if enable_vision_analysis:
                # Start vision analysis in background
                frames_task = asyncio.create_task(
                    self.video_processor.process_video(video_id, video_path)
                )

            # Wait for transcription first
            transcript = await transcript_task

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

            if callback:
                await callback(ProcessingStage.COMPLETED, 1.0, "Processing complete!")
                logger.debug(f"Updating status for {video_id}: {ProcessingStage.COMPLETED} | Data: 1.0")

            result = {
                "video_id": video_id,
                "transcript": transcript,
                "frames": frames_data,
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


class VideoService:
    def __init__(self, repository: VideoRepository, queue_provider: QueueService, cache_service: VideoCacheService, mcp_service: MCPService):
        self.repository = repository
        self.video_queue = queue_provider
        self.cache_service = cache_service
        self.mcp_manager = mcp_service
        self.pipeline = VideoPipeline(self.mcp_manager)

        # Limit GPU tasks to avoid OOM - can be tuned based on GPU capacity and model size
        self.semaphore = None  # Initialized in lifespan with num_workers

    async def ingest_video(self, video_file, video_id):
        # 1. Save the raw file first
        await self.repository.save_raw_video(video_id, video_file)

        # 2. AI Processing (OpenCV + LLM + Embedding)
        # This returns a list of dicts with descriptions and embeddings
        processed_frames = await self.ai.process_video(video_id)

        # 3. Use Repository to persist the AI data to Pinecone/Chroma
        await self.repository.save_video_metadata(video_id, processed_frames)
        
        return {"status": "success", "video_id": video_id}
    
    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""

        logger.info(f"Getting status for video: {video_id}")
        status = await self.cache_service.get_video_status(video_id)

        if status:
            return status
        else:
            meta_data = await self.repository.get_video_metadata(video_id)

            if meta_data and meta_data.process_end_time is not None:
                return VideoProcessingStatus(
                    video_id=video_id,
                    status=VideoStatus.PROCESSED,
                    current_stage=ProcessingStage.COMPLETED,
                    progress=1,
                    estimated_completion=None,
                    message="Video is already processed",
                    error=None
                )
            return None

    async def set_video_status(self, video_id: str, status: VideoProcessingStatus):
        await self.cache_service.set_video_status(video_id, status)

    async def remove_video_status(self, video_id: str):
        await self.cache_service.remove_video_status(video_id)

    async def worker(self, worker_id: int):
        logger.info(f"Worker {worker_id} started")
        try:
            while True:
                try:
                    job = await self.video_queue.pop()
                except Exception as e:
                    logger.error(f"Queue error: {e}")
                    await asyncio.sleep(2)
                    continue

                if not job:
                    await asyncio.sleep(1)
                    continue

                try:
                    video_id = job['video_id']
                    logger.info(f"Worker {worker_id} processing {video_id}")

                    video_metadata = await self.get_video_metadata(job["video_id"])

                    if not video_metadata:
                        logger.error(
                            f"Worker {worker_id} could not find metadata for video {job['video_id']}")
                        raise ValueError(
                            f"Metadata not found for video {job['video_id']}")

                    async with self.semaphore:  # type: ignore
                        await self.process_video(
                            job["video_id"],
                            video_metadata.storage_path,
                            enable_vision_analysis=job["enable_vision_analysis"]
                        )

                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {str(e)}")
                    await asyncio.sleep(1) 
                    continue
        # This is triggered by task.cancel() in the lifespan
        except asyncio.CancelledError:
            logger.info(
                f"Worker {worker_id} received shutdown signal. Cleaning up...")
        finally:
            # Perform any per-worker cleanup here
            logger.info(f"Worker {worker_id} has exited.")

    async def start(self, num_workers: int = 1):
        """Start multiple worker loops"""
        # Create the semaphore here, inside the active event loop
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(2)
            logger.info(
                "GPU Semaphore initialized within the active event loop.")

        workers = []
        for i in range(1):
            workers.append(asyncio.create_task(self.worker(i)))

        self.workers = workers

    async def end(self):
        """Gracefully stop asyncio worker tasks"""
        if not self.workers:
            return

        logger.info(f"Stopping {len(self.workers)} workers...")
        for worker in self.workers:
            worker.cancel()

        try:
            # Wait for workers to acknowledge cancellation
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("Workers timed out during shutdown.")
        finally:
            self.workers = []

    async def add_video_to_queue(self, video_id: str, enable_vision_analysis: bool = True):
        """Add video to processing queue"""
        # self.video_queue.put_nowait({
        #     "video_id": video_id,
        #     "enable_vision_analysis": enable_vision_analysis
        # })
        status = VideoProcessingStatus(
            video_id=video_id,
            status=VideoStatus.UPLOADED,
            current_stage=ProcessingStage.QUEUED,
            progress=0.0,
            estimated_completion=None,
            message="Video queued for processing",
            error=None
        )
        await self.set_video_status(video_id, status)
        await self.video_queue.push({
            "video_id": video_id,
            "enable_vision_analysis": enable_vision_analysis
        })
        logger.debug(f"Added to Queue :: {video_id}")

    async def process_video(self, video_id: str, video_path: str,
                            enable_vision_analysis: bool = True,
                            auto_load_mcp: bool = False,
                            save_results: bool = True
                            ) -> Dict[str, Any]:
        """Process a video through the pipeline"""

        # Fetch initial status from cache
        status_obj = await self.cache_service.get_video_status(video_id)
        
        if not status_obj:
            raise ValueError(f"Video {video_id} not found in processing queue")

        async def progress_callback(stage, progress, message):
            await self._update_status(
                video_id,
                status_obj,
                VideoStatus.PROCESSING,
                data={
                    "current_stage": stage,
                    "progress": progress,
                    "message": message
                }
            )
            await asyncio.sleep(0.5)

        try:
            # 1. Trigger the INITIATING stage
            await self._update_status(video_id, status_obj, VideoStatus.PROCESSING,
                                      data={"current_stage": ProcessingStage.INITIATING,
                                            "progress": 0.05,
                                            "message": "Initializing pipeline..."})

            # 2. Run pipeline (This will call progress_callback many times)
            result = await self.pipeline.process(
                video_path=video_path,
                video_id=video_id,
                enable_vision_analysis=enable_vision_analysis,
                callback=progress_callback
            )

            # 3. Save Results
            if save_results and result.get("success"):
                # Update message before saving
                await self._update_status(video_id, status_obj, VideoStatus.PROCESSING,
                                          data={"current_stage": ProcessingStage.COMPLETED,
                                                "message": "Saving results..."})
                await self._save_processing_results(video_id, result)

            # MCP Integration
            if auto_load_mcp and result.get("success"):
                mcp_result = await self.mcp_manager.load_video(video_id)
                result["mcp_loaded"] = mcp_result.get("success", False)
                if result["mcp_loaded"]:
                    logger.info(f"Auto-loaded video {video_id} to MCP")

            # 4. Final Success
            await self._update_status(video_id, status_obj, VideoStatus.PROCESSED)

            return result

        except Exception as e:
            logger.error(
                f"Pipeline Failed for {video_id}: {str(e)}", exc_info=True)
            # Ensure the DB/Cache reflects the failure
            await self._update_status(
                video_id,
                status_obj,
                VideoStatus.FAILED,
                data={"error": str(e), "current_stage": "failed"}
            )
            raise e

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
            metadata = await self.pipeline.get_metadata(video_path, video_id, file)

            # Store metadata
            await self.storage.save_video_metadata(metadata)

            # Store metadata
            await self.cache_service.set_video_metadata(video_id, metadata)
            return metadata

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise

    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""
        metadata = await self.cache_service.get_video_metadata(video_id)
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

    async def list_videos(self, page: int = 1, limit: int = 20,
                          status: Optional[str] = None) -> Tuple[List[VideoMetadata], int]:
        """List videos with pagination"""
        videos = await self.storage.list_videos(page, limit, status)

        return videos, len(videos)
        # # In production, use database
        # # For now, return from cache

        # self.storage.list_all_videos()

        # # Get from processing queue
        # for item in self.processing_table.values():
        #     all_videos.append(item)

        # # Get from results
        # for item in self.processing_results.values():
        #     all_videos.append(item)

        # # Filter by status
        # if status:
        #     all_videos = [v for v in all_videos if v.get("status") == status]

        # # Paginate
        # start_idx = (page - 1) * limit
        # end_idx = start_idx + limit
        # paginated = all_videos[start_idx:end_idx]

        # return paginated, len(all_videos)

    async def delete_video(self, video_id: str) -> bool:
        """Delete video and all associated data"""
        try:
            # Delete from storage
            success = await self.storage.delete_video_data(video_id)

            # Delete from cache
            await self.cache_service.delete(f"video:{video_id}:metadata")
            await self.cache_service.delete(f"video:{video_id}:status")
            await self.cache_service.delete(f"video:{video_id}:results")

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
            "queue_size": await self.video_queue.get_size(),
            "processed_count": await self.cache_service.get_processed_count(),
            "timestamp": datetime.now()
        }

    async def _update_status(self,
                             video_id: str,
                             status_obj: VideoProcessingStatus,
                             status: VideoStatus,
                             data: Optional[Dict] = None):

        logger.debug(f"Updating status for {video_id}: {status} | Data: {data}")
        if not status_obj:
            return

        status_obj.status = status
        status_obj.updated_at = datetime.now()

        if data:
            status_obj.current_stage = data.get(
                "current_stage", status_obj.current_stage)
            status_obj.progress = data.get("progress", status_obj.progress)
            status_obj.message = data.get("message", status_obj.message)
            status_obj.error = data.get("error", status_obj.error)
            status_obj.estimated_completion = data.get(
                "estimated_completion", status_obj.estimated_completion)

        if status == VideoStatus.PROCESSED or status == VideoStatus.FAILED:
            status_obj.progress = 1.0
            # If no message was passed in 'data', set a default
            if not data or "message" not in data:
                status_obj.message = "Processing completed" if status == VideoStatus.PROCESSED else "Processing failed"

            status_obj.estimated_completion = datetime.now()

            # Sync to permanent storage
            metadata = await self.storage.get_video_metadata(video_id)
            if metadata:
                metadata.process_start_time = status_obj.created_at
                metadata.process_end_time = datetime.now()
                metadata.status = status
                await self.storage.save_video_metadata(metadata)

        # CRITICAL: Always push to cache so the frontend sees the update
        await self.cache_service.set_video_status(video_id, status_obj)

    async def _save_processing_results(self, video_id: str, result: Dict[str, Any]):
        """Save processing results to storage"""

        logger.debug(f"Saving processing results for video {video_id}...")

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
        await self.cache_service.set_video_results(video_id, result)

        logger.debug(
            f"Processing results for video {video_id} saved successfully")
