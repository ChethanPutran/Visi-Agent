from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from src.shared.contracts.video_metadata import VideoMetadata

class VideoUploadRequest(BaseModel):
    """Schema for video upload request"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the video")
    file_size: int = Field(..., description="File size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

class VideoUploadResponse(BaseModel):
    """Schema for video upload response"""
    success: bool = Field(..., description="Whether upload was successful")
    video_id: str = Field(..., description="Unique video ID")
    message: str = Field(..., description="Response message")
    metadata: VideoMetadata = Field(..., description="Video metadata")
    upload_url: Optional[str] = Field(
        None, description="Direct upload URL (for S3)")
    upload_time: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), 
    description="Upload timestamp")


class BatchUploadResult(BaseModel):
    """Result for a single video in batch upload"""
    video_id: str = Field(..., description="Video ID")
    filename: str = Field(..., description="Original filename")
    success: bool = Field(..., description="Whether upload was successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[VideoMetadata] = Field(
        None, description="Video metadata if successful")


class BatchUploadRequest(BaseModel):
    """Schema for batch video upload request"""
    videos: List[VideoUploadRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of videos to upload"
    )
    process_immediately: bool = Field(
        default=True,
        description="Start processing videos immediately after upload"
    )
    enable_vision_analysis: bool = Field(
        default=True,
        description="Enable GPT-4 Vision analysis for all videos"
    )
    batch_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the entire batch"
    )

    @validator('videos')
    def validate_unique_filenames(cls, videos):
        filenames = [video.filename for video in videos]
        if len(filenames) != len(set(filenames)):
            raise ValueError('Filenames must be unique within a batch')
        return videos


class BatchUploadResponse(BaseModel):
    """Schema for batch upload response"""
    success: bool = Field(..., description="Overall success")
    message: str = Field(..., description="Response message")
    total_videos: int = Field(..., description="Total number of videos")
    successful_uploads: int = Field(...,
                                    description="Number of successful uploads")
    failed_uploads: int = Field(..., description="Number of failed uploads")
    results: List[BatchUploadResult] = Field(...,
                                             description="Individual results")
    batch_id: Optional[str] = Field(None, description="Batch ID for tracking")
