from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums for response status
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"
    PROCESSING = "processing"

class ErrorCode(str, Enum):
    # General errors
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    
    # Video processing errors
    VIDEO_PROCESSING_ERROR = "video_processing_error"
    TRANSCRIPTION_ERROR = "transcription_error"
    VISION_ANALYSIS_ERROR = "vision_analysis_error"
    SUMMARY_ERROR = "summary_error"
    
    # Query errors
    QUERY_ERROR = "query_error"
    SEARCH_ERROR = "search_error"
    CONTEXT_TOO_LARGE = "context_too_large"
    
    # External service errors
    OPENAI_ERROR = "openai_error"
    STORAGE_ERROR = "storage_error"
    VECTOR_DB_ERROR = "vector_db_error"
    
    # System errors
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT_ERROR = "timeout_error"

# Base response schemas
class BaseResponse(BaseModel):
    """Base schema for all API responses"""
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SuccessResponse(BaseResponse):
    """Schema for successful responses"""
    data: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Response data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {},
                "metadata": {}
            }
        }

class ErrorDetail(BaseModel):
    """Schema for error details"""
    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Detailed error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    value: Optional[Any] = Field(None, description="Value that caused the error")
    suggestion: Optional[str] = Field(None, description="Suggested fix")

class ErrorResponse(BaseResponse):
    """Schema for error responses"""
    error: ErrorDetail = Field(..., description="Error details")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "An error occurred",
                "timestamp": "2024-01-15T10:30:00Z",
                "error": {
                    "code": "validation_error",
                    "message": "Invalid input provided",
                    "field": "video_id",
                    "value": "invalid-id",
                    "suggestion": "Provide a valid video ID"
                },
                "trace_id": "trace-123456"
            }
        }

class PaginatedResponse(BaseModel):
    """Base schema for paginated responses"""
    items: List[Any] = Field(..., description="List of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    has_more: bool = Field(..., description="Whether there are more items")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    prev_cursor: Optional[str] = Field(None, description="Cursor for previous page")

# Query response schemas
class QueryResult(BaseModel):
    """Schema for a single query result"""
    content: str = Field(..., description="Result content")
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    source: str = Field(..., description="Source of result: transcript, vision, summary")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SearchResult(BaseModel):
    """Schema for a search result"""
    content: str = Field(..., description="Result content")
    timestamp: float = Field(..., ge=0.0, description="Timestamp in seconds")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    source: str = Field(..., description="Source type: transcript, vision")
    type: str = Field(..., description="Result type: exact_match, semantic_match")
    context_before: Optional[str] = Field(None, description="Context before the match")
    context_after: Optional[str] = Field(None, description="Context after the match")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class VideoQueryResponse(SuccessResponse):
    """Schema for video query response"""
    video_id: str = Field(..., description="Video ID")
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    timestamps: List[float] = Field(default_factory=list, description="Relevant timestamps")
    sources: List[QueryResult] = Field(default_factory=list, description="Source results")
    processing_time: float = Field(..., description="Processing time in seconds")
    tokens_used: Optional[int] = Field(None, description="Tokens used for generation")
    model: Optional[str] = Field(None, description="Model used for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Query processed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "video_id": "vid_123",
                "question": "What are the main topics discussed?",
                "answer": "The main topics discussed are...",
                "confidence": 0.85,
                "timestamps": [15.2, 45.8, 120.5],
                "sources": [],
                "processing_time": 2.5,
                "tokens_used": 450,
                "model": "gpt-4"
            }
        }

class TemporalQueryResponse(VideoQueryResponse):
    """Schema for temporal query response"""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    duration: float = Field(..., description="Duration of timeframe in seconds")

class ComparativeQueryResponse(VideoQueryResponse):
    """Schema for comparative query response"""
    timeframe1: Dict[str, float] = Field(..., description="First timeframe")
    timeframe2: Dict[str, float] = Field(..., description="Second timeframe")
    similarities: List[str] = Field(default_factory=list, description="Similarities")
    differences: List[str] = Field(default_factory=list, description="Differences")

class SearchResponse(SuccessResponse):
    """Schema for search response"""
    video_id: str = Field(..., description="Video ID")
    query: str = Field(..., description="Search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time: float = Field(..., description="Search time in seconds")
    search_type: str = Field(..., description="Type of search performed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Search completed successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "video_id": "vid_123",
                "query": "car red driver",
                "results": [],
                "total_results": 5,
                "search_time": 0.25,
                "search_type": "semantic"
            }
        }

class PaginatedSearchResponse(PaginatedResponse):
    """Schema for paginated search response"""
    video_id: str = Field(..., description="Video ID")
    query: str = Field(..., description="Search query")
    search_type: str = Field(..., description="Type of search")
    search_time: float = Field(..., description="Search time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_123",
                "query": "car red driver",
                "search_type": "semantic",
                "search_time": 0.25,
                "items": [],
                "page": 1,
                "limit": 10,
                "total": 25,
                "has_more": True
            }
        }

# Multi-video response schemas
class MultiVideoResult(BaseModel):
    """Schema for a single video result in multi-video query"""
    video_id: str = Field(..., description="Video ID")
    answer: str = Field(..., description="Answer for this video")
    confidence: float = Field(..., description="Confidence score")
    relevant_timestamps: List[float] = Field(default_factory=list, description="Relevant timestamps")
    processing_time: float = Field(..., description="Processing time for this video")

class MultiVideoQueryResponse(SuccessResponse):
    """Schema for multi-video query response"""
    question: str = Field(..., description="Original question")
    combined_answer: Optional[str] = Field(None, description="Combined answer across videos")
    per_video_results: List[MultiVideoResult] = Field(..., description="Results per video")
    comparison_summary: Optional[str] = Field(None, description="Comparison summary")
    total_processing_time: float = Field(..., description="Total processing time")
    videos_processed: int = Field(..., description="Number of videos processed")

# Batch query response schemas
class BatchQueryResult(BaseModel):
    """Schema for a single batch query result"""
    query_id: Optional[str] = Field(None, description="Query ID")
    video_id: str = Field(..., description="Video ID")
    question: str = Field(..., description="Question")
    answer: str = Field(..., description="Answer")
    status: ResponseStatus = Field(..., description="Query status")
    processing_time: float = Field(..., description="Processing time")
    error: Optional[ErrorDetail] = Field(None, description="Error details if failed")

class BatchQueryResponse(SuccessResponse):
    """Schema for batch query response"""
    batch_id: str = Field(..., description="Batch ID")
    results: List[BatchQueryResult] = Field(..., description="Batch results")
    total_queries: int = Field(..., description="Total number of queries")
    successful_queries: int = Field(..., description="Number of successful queries")
    failed_queries: int = Field(..., description="Number of failed queries")
    total_processing_time: float = Field(..., description="Total processing time")

# Follow-up query response schemas
class FollowUpQueryResponse(VideoQueryResponse):
    """Schema for follow-up query response"""
    original_query_id: str = Field(..., description="Original query ID")
    conversation_context: Optional[str] = Field(None, description="Conversation context")
    is_follow_up: bool = Field(default=True, description="Whether this is a follow-up")

# Statistics response schemas
class QueryStatistics(BaseModel):
    """Schema for query statistics"""
    total_queries: int = Field(..., description="Total queries processed")
    successful_queries: int = Field(..., description="Successful queries")
    failed_queries: int = Field(..., description="Failed queries")
    average_processing_time: float = Field(..., description="Average processing time")
    average_confidence: float = Field(..., description="Average confidence score")
    most_common_queries: List[Dict[str, Any]] = Field(..., description="Most common queries")
    tokens_used: int = Field(..., description="Total tokens used")
    cost_estimate: float = Field(..., description="Estimated cost")

class VideoStatisticsResponse(SuccessResponse):
    """Schema for video statistics response"""
    video_id: str = Field(..., description="Video ID")
    query_statistics: QueryStatistics = Field(..., description="Query statistics")
    processing_statistics: Dict[str, Any] = Field(..., description="Processing statistics")
    storage_statistics: Dict[str, Any] = Field(..., description="Storage statistics")
    usage_statistics: Dict[str, Any] = Field(..., description="Usage statistics")

class SystemStatisticsResponse(SuccessResponse):
    """Schema for system statistics response"""
    total_videos: int = Field(..., description="Total videos processed")
    total_queries: int = Field(..., description="Total queries processed")
    total_processing_time: float = Field(..., description="Total processing time")
    average_query_time: float = Field(..., description="Average query time")
    active_users: int = Field(..., description="Active users")
    system_load: Dict[str, float] = Field(..., description="System load statistics")
    api_usage: Dict[str, Any] = Field(..., description="API usage statistics")

# Webhook response schemas
class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    webhook_id: str = Field(..., description="Webhook ID")
    event_type: str = Field(..., description="Event type")
    video_id: str = Field(..., description="Video ID")
    status: str = Field(..., description="Delivery status")
    attempt: int = Field(..., description="Attempt number")
    response_code: Optional[int] = Field(None, description="HTTP response code")
    response_body: Optional[str] = Field(None, description="Response body")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

# Export response schemas
class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    PDF = "pdf"
    MARKDOWN = "markdown"

class ExportRequest(BaseModel):
    """Schema for export request"""
    video_id: str = Field(..., description="Video ID")
    format: ExportFormat = Field(..., description="Export format")
    include_transcript: bool = Field(default=True, description="Include transcript")
    include_summary: bool = Field(default=True, description="Include summary")
    include_analysis: bool = Field(default=False, description="Include analysis")
    include_queries: bool = Field(default=False, description="Include query history")

class ExportResponse(SuccessResponse):
    """Schema for export response"""
    video_id: str = Field(..., description="Video ID")
    export_id: str = Field(..., description="Export ID")
    format: ExportFormat = Field(..., description="Export format")
    download_url: str = Field(..., description="Download URL")
    file_size: int = Field(..., description="File size in bytes")
    expires_at: datetime = Field(..., description="Expiration timestamp")

# Health check response schemas
class HealthCheckResponse(BaseResponse):
    """Schema for health check response"""
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Uptime in seconds")
    dependencies: Dict[str, bool] = Field(..., description="Dependency status")
    checks: List[Dict[str, Any]] = Field(..., description="Health checks")

class ServiceStatus(BaseModel):
    """Schema for service status"""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    latency: Optional[float] = Field(None, description="Service latency")
    last_check: datetime = Field(..., description="Last check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class SystemStatusResponse(SuccessResponse):
    """Schema for system status response"""
    overall_status: str = Field(..., description="Overall system status")
    services: List[ServiceStatus] = Field(..., description="Service statuses")
    system_metrics: Dict[str, Any] = Field(..., description="System metrics")
    last_updated: datetime = Field(..., description="Last update timestamp")