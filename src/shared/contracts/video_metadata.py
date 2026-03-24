from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VideoFormat(str, Enum):
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"


class VideoMetadata(BaseModel):
    """Schema for video metadata"""
    id: str = Field(..., description="Unique video ID")
    filename: str = Field(..., description="Filename")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    duration: Optional[float] = Field(
        None, description="Video duration in seconds")
    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")
    fps: Optional[float] = Field(None, description="Frames per second")
    format: VideoFormat = Field(..., description="Video format")
    upload_time: datetime = Field(..., description="Upload timestamp")
    thumbnail_path: Optional[str] = Field(None, description="Path to video thumbnail image")
    process_start_time: Optional[datetime] = Field(
        None, description="Processing start time")
    process_end_time: Optional[datetime] = Field(
        None, description="Processing end time")
    transcript_available: bool = Field(
        default=False, description="Whether transcript is available")
    summary_available: bool = Field(
        default=False, description="Whether summary is available")
    vision_analysis_available: bool = Field(
        default=False, description="Whether vision analysis is available")
    transcript_word_count: Optional[int] = Field(
        None, description="Number of words in transcript")
    frame_count: Optional[int] = Field(
        None, description="Number of frames analyzed")
    processing_time: Optional[float] = Field(
        None, description="Total processing time in seconds")
    storage_path: str = Field(..., description="Path to stored video")
    storage_type: str = Field(
        default="local", description="Storage type: local, s3, etc.")
    tags: List[str] = Field(default_factory=list, description="Video tags")
