
# Request schemas
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from src.shared.contracts.video_metadata import VideoFormat


class VideoStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    FRAME_EXTRACTION = "frame_extraction"
    VISION_ANALYSIS = "vision_analysis"
    SUMMARIZATION = "summarization"
    INDEXING = "indexing"
    INITIATING = "initiating"
    NOT_STARTED = "not_started"


class VideoProcessingRequest(BaseModel):
    """Schema for video processing request"""
    video_id: str = Field(..., description="ID of the video to process")
    enable_vision_analysis: bool = Field(
        default=True,
        description="Whether to enable GPT-4 Vision analysis"
    )
    enable_summarization: bool = Field(
        default=True,
        description="Whether to generate a summary"
    )
    frame_interval: int = Field(
        default=2,
        ge=1,
        le=30,
        description="Interval in seconds between frames to analyze"
    )
    whisper_model: str = Field(
        default="base",
        description="Whisper model to use for transcription"
    )


class ProcessingStageInfo(BaseModel):
    """Information about a processing stage"""
    stage: ProcessingStage = Field(..., description="Processing stage")
    status: str = Field(..., description="Stage status")
    start_time: Optional[datetime] = Field(
        None, description="Stage start time")
    end_time: Optional[datetime] = Field(None, description="Stage end time")
    duration: Optional[float] = Field(
        None, description="Stage duration in seconds")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Progress (0.0 to 1.0)")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class VideoProcessingStatus(BaseModel):
    """Schema for video processing status"""
    video_id: str = Field(..., description="Video ID")
    status: str = Field(..., description="Overall status")
    current_stage: Optional[ProcessingStage] = Field(
        None, description="Current processing stage")
    progress: float = Field(0.0, ge=0.0, le=1.0,
                            description="Overall progress (0.0 to 1.0)")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time")
    stages: List[ProcessingStageInfo] = Field(
        default_factory=list, description="Stage information")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Status timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatchVideoRequest(BaseModel):
    """Schema for batch video processing"""
    video_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of video IDs to process"
    )
    parallel_processing: bool = Field(
        default=True,
        description="Whether to process videos in parallel"
    )
    options: Optional[VideoProcessingRequest] = Field(
        default=None,
        description="Processing options for all videos"
    )
