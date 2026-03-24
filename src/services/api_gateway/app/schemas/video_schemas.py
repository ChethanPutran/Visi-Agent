from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from src.shared.contracts.video_metadata import VideoMetadata

# Enums for video processing


class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoSearchRequest(BaseModel):
    """Schema for searching within a video"""
    query: str = Field(..., min_length=1, max_length=500,
                       description="Search query")
    search_type: str = Field(
        default="semantic",
        description="Type of search: semantic, keyword, hybrid"
    )
    max_results: int = Field(default=10, ge=1, le=100,
                             description="Maximum results")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0,
                             description="Similarity threshold")


class VideoListResponse(BaseModel):
    """Schema for video list response"""
    videos: List[VideoMetadata] = Field(..., description="List of videos")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Results per page")
    total: int = Field(..., ge=0, description="Total number of videos")
    has_more: bool = Field(..., description="Whether there are more results")
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Applied filters")


class TranscriptSegment(BaseModel):
    """Schema for a single transcript segment"""
    id: str = Field(..., description="Segment ID")
    start: float = Field(..., ge=0.0, description="Start time in seconds")
    end: float = Field(..., ge=0.0, description="End time in seconds")
    text: str = Field(..., description="Transcribed text")
    speaker: Optional[str] = Field(None, description="Speaker identifier")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Confidence score")
    words: Optional[List[Dict[str, Any]]] = Field(
        None, description="Word-level details")


class VideoTranscript(BaseModel):
    """Schema for video transcript"""
    video_id: str = Field(..., description="Video ID")
    segments: List[TranscriptSegment] = Field(
        ..., description="Transcript segments")
    language: Optional[str] = Field(None, description="Detected language")
    duration: float = Field(..., ge=0.0, description="Video duration")
    word_count: int = Field(..., ge=0, description="Total word count")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FrameAnalysis(BaseModel):
    """Schema for frame analysis"""
    timestamp: float = Field(..., ge=0.0,
                             description="Frame timestamp in seconds")
    description: str = Field(...,
                             description="Frame description from vision model")
    objects: Optional[List[Dict[str, Any]]] = Field(
        None, description="Detected objects")
    colors: Optional[List[str]] = Field(None, description="Dominant colors")
    text: Optional[str] = Field(None, description="Extracted text from frame")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Analysis confidence")
    frame_url: Optional[str] = Field(
        None, description="URL to the frame image")


class VideoAnalysis(BaseModel):
    """Schema for video analysis results"""
    video_id: str = Field(..., description="Video ID")
    frames: List[FrameAnalysis] = Field(..., description="Analyzed frames")
    total_frames: int = Field(..., description="Total frames analyzed")
    frame_interval: int = Field(...,
                                description="Interval between analyzed frames")
    created_at: datetime = Field(..., description="Analysis timestamp")


class VideoSummary(BaseModel):
    """Schema for video summary"""
    video_id: str = Field(..., description="Video ID")
    summary: str = Field(..., description="Summary text")
    key_points: List[str] = Field(..., description="Key points")
    topics: List[str] = Field(..., description="Main topics")
    duration: str = Field(..., description="Formatted duration (e.g., '5:30')")
    word_count: int = Field(..., description="Summary word count")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Statistics schemas


class VideoStatistics(BaseModel):
    """Schema for video statistics"""
    video_id: str = Field(..., description="Video ID")
    total_processing_time: float = Field(...,
                                         description="Total processing time in seconds")
    transcription_time: Optional[float] = Field(
        None, description="Transcription time")
    vision_analysis_time: Optional[float] = Field(
        None, description="Vision analysis time")
    summary_generation_time: Optional[float] = Field(
        None, description="Summary generation time")
    api_calls: int = Field(..., description="Number of API calls made")
    tokens_used: int = Field(..., description="Total tokens used")
    cost_estimate: Optional[float] = Field(
        None, description="Estimated cost in USD")


class StorageInfo(BaseModel):
    """Schema for storage information"""
    video_id: str = Field(..., description="Video ID")
    original_size: int = Field(..., description="Original video size in bytes")
    processed_size: int = Field(..., description="Total processed data size")
    transcript_size: int = Field(..., description="Transcript file size")
    analysis_size: int = Field(..., description="Analysis data size")
    total_size: int = Field(..., description="Total storage used")
    storage_location: str = Field(..., description="Storage location/type")

    @property
    def original_size_mb(self) -> float:
        """Get original size in MB"""
        return self.original_size / (1024 * 1024)

    @property
    def total_size_mb(self) -> float:
        """Get total size in MB"""
        return self.total_size / (1024 * 1024)

# Webhook schemas


class VideoWebhookPayload(BaseModel):
    """Schema for video webhook payload"""
    event_type: str = Field(..., description="Event type")
    video_id: str = Field(..., description="Video ID")
    status: VideoStatus = Field(..., description="Current status")
    metadata: VideoMetadata = Field(..., description="Video metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp")
    payload: Optional[Dict[str, Any]] = Field(
        None, description="Additional payload")


class WebhookRegistration(BaseModel):
    """Schema for webhook registration"""
    url: str = Field(..., description="Webhook URL")
    secret: Optional[str] = Field(
        None, description="Webhook secret for verification")
    events: List[str] = Field(..., description="Events to subscribe to")
    enabled: bool = Field(
        default=True, description="Whether webhook is enabled")
