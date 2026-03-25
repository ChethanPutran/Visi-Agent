import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from fastapi import UploadFile
from src.services.llm_service.app.llm_service import LLMService
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.storage.repository.video_repository import VideoRepository
from src.shared.storage.factories import QueueService
from src.shared.contracts.video_metadata import VideoMetadata
from src.services.api_gateway.app.schemas.video_schemas import VideoStatus
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus, ProcessingStage
from src.shared.logging.logger import get_logger
from src.services.video_processing.app.processors.video_pipeline import VideoPipeline

logger = get_logger(__name__)

class VideoService:
    def __init__(self, repository: VideoRepository, queue_provider: QueueService, mcp_service: LLMService,
                 pipeline: VideoPipeline):
        self.repository = repository
        self.video_queue = queue_provider
        self.mcp_manager = mcp_service
        self.pipeline = pipeline

        # Limit GPU tasks to avoid OOM - can be tuned based on GPU capacity and model size
        self.semaphore = None  # Initialized in lifespan with num_workers
    
    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""

        logger.info(f"Getting status for video: {video_id}")
        status = await self.repository.get_video_status(video_id)

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
        await self.repository.set_video_status(video_id, status)

    async def remove_video_status(self, video_id: str):
        await self.repository.remove_video_status(video_id)

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
                        entries = await self.process_video(
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
        status_obj = await self.repository.get_video_status(video_id)
        
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
            video_path = await self.repository.save_video(file, video_id)
            metadata = await self.pipeline.get_metadata(video_path, video_id, file)

            # Store metadata
            await self.repository.save_video_metadata(metadata)

            return metadata

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            raise

    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""
        metadata = await self.repository.get_video_metadata(video_id)
        return metadata

    async def get_video_transcript(self, video_id: str, format: str = "json") -> Optional[Any]:
        """Get video transcript"""
        try:
            transcript = await self.repository.get_transcript(video_id, format)
            return transcript
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            return None

    async def get_video_summary(self, video_id: str) -> Optional[str]:
        """Get video summary"""
        try:
            summary = await self.repository.get_summary(video_id)
            return summary
        except Exception as e:
            logger.error(f"Error getting summary: {str(e)}")
            return None

    async def list_videos(self, page: int = 1, limit: int = 20,
                          status: Optional[str] = None) -> Tuple[List[VideoMetadata], int]:
        """List videos with pagination"""
        videos = await self.repository.list_videos(page, limit, status)

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
            # Delete from cache
            success = await self.repository.delete_video_data(video_id)
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
            "processed_count": await self.repository.get_processed_count(),
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
            metadata = await self.repository.get_video_metadata(video_id)
            if metadata:
                metadata.process_start_time = status_obj.created_at
                metadata.process_end_time = datetime.now()
                metadata.status = status
                await self.repository.save_video_metadata(metadata)

        # CRITICAL: Always push to cache so the frontend sees the update
        await self.repository.set_video_status(video_id, status_obj)

    async def _save_processing_results(self, video_id: str, result: Dict[str, Any]):
        """Save processing results to storage"""

        logger.debug(f"Saving processing results for video {video_id}...")

        # Save transcript
        if "transcript" in result:
            await self.repository.save_transcript(video_id, result["transcript"])

        # Save summary
        if "summary" in result:
            await self.repository.save_summary(video_id, result["summary"])

        # Save frames data
        if "frames" in result:
            await self.repository.save_frames(video_id, result["frames"])

        # Cache results
        await self.repository.set_video_results(video_id, result)

        # Save embeddings
        if "embeddings" in result:
            await self.repository.save_embeddings(video_id, result["embeddings"])

        logger.debug(
            f"Processing results for video {video_id} saved successfully")
