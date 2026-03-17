from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
import uuid
import logging

from src.services.api_gateway.app.schemas.video_schemas import VideoListResponse
from src.services.video_ingestion.app.contracts.schemas import VideoUploadResponse, BatchUploadResponse
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.logging.logger import get_logger
from src.services.video_ingestion.app.handlers.video_service import VideoService
from src.services.api_gateway.app.dependencies.services import get_video_service


logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    prcess_immediately: bool = Form(True),
    file: UploadFile = File(...),
    enable_vision_analysis: bool = Form(True),
    video_service: VideoService = Depends(get_video_service)
):
    """
    Upload a video file for processing

    - file: Video file to upload (mp4, mov, avi, etc.)
    - process_immediately: Whether to start processing immediately
    - enable_vision_analysis: Whether to enable GPT-4 Vision analysis
    """
    try:
        logger.log(logging.DEBUG, f"Request to endpoint video: {file.filename}")
        # Validate file
        if not file.content_type or (not file.content_type .startswith("video/")):
            raise HTTPException(
                status_code=400,
                detail="File must be a video"
            )
        logger.log(logging.DEBUG, f"Uploading video: {file.filename}")

        # Upload and get the meta data of the video
        metadata = await video_service.upload_video(file=file)

        logger.log(logging.DEBUG, f"Video uploaded successfully: {metadata.id} - {metadata.filename}")

        if prcess_immediately:
            # Schedule processing
            video_service.add_video_to_queue(metadata.id, enable_vision_analysis=enable_vision_analysis)

        # Return response
        return VideoUploadResponse(
            success=True,
            video_id=metadata.id,
            metadata=metadata,
            message="Video uploaded successfully",
            upload_url=metadata.storage_path,
            upload_time=metadata.upload_time,
        )

    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_videos_batch(
    files: List[UploadFile] = File(...),
    enable_vision_analysis: bool = Form(True),
    video_service: VideoService = Depends(get_video_service)
):
    """
    Upload multiple videos in batch
    """
    try:
        results = []
        valid = True
        for file in files:
            if (not file) or (not file.content_type):
                valid = False
                break

        # Validate file
        if not valid:
            raise HTTPException(
                status_code=400,
                detail="File must be a video"
            )
        logger.log(logging.DEBUG, f"Uploading videos... Batch size: {len(files)}")

        meta_datas = await video_service.upload_batch_videos(files=files)

        for file, meta_data in zip(files, meta_datas):
            video_id = meta_data.id

            # Schedule processing
            video_service.add_video_to_queue(video_id, enable_vision_analysis=enable_vision_analysis)

            results.append({
                "video_id": video_id,
                "filename": file.filename,
                "success": True
            })

        successful_count = len([r for r in results if r['success']])
        failed_count = len([r for r in results if not r['success']])

        return BatchUploadResponse(
            success=True,
            message=f"Batch upload completed: {successful_count} successful, {failed_count} failed",
            total_videos=len(files),
            batch_id=str(uuid.uuid4()),
            results=results,
            successful_uploads=successful_count,
            failed_uploads=failed_count
        )

    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/status", response_model=VideoProcessingStatus)
def get_video_status(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Get the processing status of a video
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/status: {video_id}")
    print(f"Getting status for video: {video_id}")
    try:
        status = video_service.get_video_status(video_id)

        if not status:
            raise HTTPException(status_code=404, detail="Video not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/metadata", response_model=VideoMetadata)
async def get_video_metadata(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Get metadata for a specific video
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/metadata: {video_id}")
    try:
        metadata = await video_service.get_video_metadata(video_id)

        if not metadata:
            raise HTTPException(status_code=404, detail="Video not found")

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    video_service: VideoService = Depends(get_video_service)
):
    """
    List all videos with pagination and filtering
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/list")
    try:
        videos, total = await video_service.list_videos(
            page=page,
            limit=limit,
            status=status
        )

        return VideoListResponse(
            videos=videos,
            page=page,
            limit=limit,
            total=total,
            has_more=(page * limit) < total,
            filters=None
        )

    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{video_id}/process")
async def process_video(
    video_id: str,
    enable_vision_analysis: bool = True,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Manually trigger processing for a video
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/process: {video_id}")

    # Get video metadata
    metadata = await video_service.get_video_metadata(video_id)
    print(metadata)
    if not metadata:
        raise HTTPException(status_code=404, detail="Video not found")

    # Shedule processing
    video_service.add_video_to_queue(video_id, enable_vision_analysis=enable_vision_analysis)

    return JSONResponse(content={
        "success": True,
        "message": f"Video {video_id} queued for processing",
        "video_id": video_id
    })

    # except Exception as e:
    #     logger.error(
    #         f"Error triggering processing for video {video_id}: {str(e)}")
    #     raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Delete a video and all its processed data
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/delete: {video_id}")
    try:
        success = await video_service.delete_video(video_id)

        if not success:
            raise HTTPException(status_code=404, detail="Video not found")

        return {
            "success": True,
            "message": f"Video {video_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/transcript")
async def get_video_transcript(
    video_id: str,
    format: str = "json",  # json, text, srt
    video_service: VideoService = Depends(get_video_service)
):
    """
    Get the transcript for a video
    """
    logger.log(
        logging.DEBUG, f"Request to endpoint video/transcript: {video_id}")
    try:
        transcript = await video_service.get_video_transcript(video_id, format)

        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")

        if format == "text":
            return transcript
        elif format == "srt":
            return StreamingResponse(
                iter([transcript]),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename={video_id}.srt"}
            )
        else:  # json
            return JSONResponse(content=transcript)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting transcript for video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/summary")
async def get_video_summary(
    video_id: str,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Get the summary for a video
    """
    logger.log(logging.DEBUG, f"Request to endpoint video/summary: {video_id}")
    try:
        summary = await video_service.get_video_summary(video_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")

        return {
            "video_id": video_id,
            "summary": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary for video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
