from pydantic import BaseModel, Field, validator, confloat, conint
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums for query types


class QueryType(str, Enum):
    GENERAL = "general"
    TEMPORAL = "temporal"
    COMPARATIVE = "comparative"
    SEARCH = "search"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"


class SearchType(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    SIMILARITY = "similarity"


class DetailLevel(str, Enum):
    BRIEF = "brief"
    DETAILED = "detailed"
    VERBOSE = "verbose"


class SortOrder(str, Enum):
    RELEVANCE = "relevance"
    CHRONOLOGICAL = "chronological"
    REVERSE_CHRONOLOGICAL = "reverse_chronological"

# Base query schemas


class BaseVideoQuery(BaseModel):
    """Base schema for video queries"""
    video_id: str = Field(..., description="ID of the video to query")
    question: Optional[str] = Field(
        None, description="Question about the video")
    include_timestamps: bool = Field(
        default=True,
        description="Whether to include timestamps in response"
    )
    include_sources: bool = Field(
        default=False,
        description="Whether to include source references"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for results"
    )
    context_window: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Context window size in tokens"
    )

# Specific query schemas


class VideoQueryRequest(BaseVideoQuery):
    """Schema for general video query request"""
    query_type: QueryType = Field(
        default=QueryType.GENERAL, description="Type of query")
    detail_level: DetailLevel = Field(
        default=DetailLevel.DETAILED, description="Detail level")
    language: Optional[str] = Field(
        default="en",
        description="Language for response"
    )
    format: Optional[str] = Field(
        default="text",
        description="Response format: text, json, markdown"
    )

    @validator("question")
    def validate_question(cls, v, values):
        """Validate that question is provided for general queries"""
        if values.get("query_type") == QueryType.GENERAL and not v:
            raise ValueError("Question is required for general queries")
        return v


class TemporalQueryRequest(BaseVideoQuery):
    """Schema for temporal range query"""
    start_time: float = Field(..., ge=0.0, description="Start time in seconds")
    end_time: float = Field(..., ge=0.0, description="End time in seconds")
    detail_level: DetailLevel = Field(
        default=DetailLevel.DETAILED, description="Detail level")

    @validator("end_time")
    def validate_time_range(cls, v, values):
        """Validate that end time is after start time"""
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("End time must be greater than start time")
        return v


class Timeframe(BaseModel):
    """Schema for a timeframe"""
    start: float = Field(..., ge=0.0, description="Start time in seconds")
    end: float = Field(..., ge=0.0, description="End time in seconds")
    label: Optional[str] = Field(None, description="Optional timeframe label")

    @validator("end")
    def validate_end_time(cls, v, values):
        if "start" in values and v <= values["start"]:
            raise ValueError("End time must be greater than start time")
        return v


class ComparativeQueryRequest(BaseVideoQuery):
    """Schema for comparative query between timeframes"""
    timeframe1: Timeframe = Field(..., description="First timeframe")
    timeframe2: Timeframe = Field(..., description="Second timeframe")
    comparison_aspects: List[str] = Field(
        default_factory=list,
        description="Specific aspects to compare"
    )
    include_differences: bool = Field(
        default=True, description="Include differences")
    include_similarities: bool = Field(
        default=True, description="Include similarities")


class SearchQueryRequest(BaseVideoQuery):
    """Schema for content search query"""
    query: str = Field(..., min_length=1, max_length=500,
                       description="Search query")
    search_type: SearchType = Field(
        default=SearchType.SEMANTIC, description="Type of search")
    sort_by: SortOrder = Field(
        default=SortOrder.RELEVANCE, description="Sort order")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filters for search results"
    )
    include_exact_matches: bool = Field(
        default=True,
        description="Include exact keyword matches"
    )
    semantic_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for semantic search vs keyword"
    )


class SummarizationRequest(BaseVideoQuery):
    """Schema for summarization request"""
    length: str = Field(
        default="medium",
        description="Summary length: short, medium, long, bullet"
    )
    focus: Optional[str] = Field(
        None,
        description="Specific focus for summary (e.g., 'technical details', 'main points')"
    )
    include_bullet_points: bool = Field(
        default=True, description="Include bullet points")
    include_keywords: bool = Field(
        default=True, description="Include keywords")
    include_timestamps: bool = Field(
        default=False, description="Include timestamps in summary")


class AnalysisRequest(BaseVideoQuery):
    """Schema for analysis request"""
    analysis_type: str = Field(
        default="content",
        description="Type of analysis: content, sentiment, topics, patterns"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Analysis parameters"
    )
    include_visual_analysis: bool = Field(
        default=True,
        description="Include visual analysis"
    )
    include_audio_analysis: bool = Field(
        default=True,
        description="Include audio/transcript analysis"
    )


class VideoQueryResponse(BaseModel):
    """Schema for a query template"""
    video_id: str = Field(..., description="Video ID")
    question: str = Field(..., description="Question asked")
    answer: str = Field(..., description="Answer for the question")
    sources: Optional[List[Dict[str, str]]
                      ] = Field(..., description="Sources refered")
    timestamps: List[float] = Field(
        default_factory=list, description="Relevant timestamps in seconds"
    )
    confidence: float = Field(
        default=0, description="Confidence for the answer")
    success: bool = Field(default=True, description="Flag indicating sucess")


class MultiVideoQueryRequest(BaseModel):
    """Schema for querying multiple videos"""
    video_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of video IDs to query"
    )
    question: str = Field(..., description="Question about the videos")
    compare_videos: bool = Field(
        default=False,
        description="Whether to compare videos or combine results"
    )
    aggregation_method: str = Field(
        default="combine",
        description="How to aggregate results: combine, compare, summarize"
    )
    include_per_video_results: bool = Field(
        default=True,
        description="Include results for each video"
    )

# Batch query schemas


class BatchQueryItem(BaseModel):
    """Schema for a single query in batch"""
    question: str = Field(..., description="Question to ask")
    video_id: str = Field(..., description="Video ID")
    query_id: Optional[str] = Field(
        None, description="Optional query ID for tracking")


class BatchQueryRequest(BaseModel):
    """Schema for batch query request"""
    queries: List[BatchQueryItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of queries to process"
    )
    parallel_processing: bool = Field(
        default=True,
        description="Process queries in parallel"
    )
    batch_id: Optional[str] = Field(None, description="Batch ID for tracking")

# Follow-up query schemas


class FollowUpQueryRequest(BaseModel):
    """Schema for follow-up query"""
    original_query_id: str = Field(..., description="ID of the original query")
    follow_up_question: str = Field(..., description="Follow-up question")
    include_context: bool = Field(
        default=True,
        description="Include context from original query"
    )
    context_window: Optional[int] = Field(
        None,
        description="Context window size for conversation"
    )

# Query suggestions


class QuerySuggestion(BaseModel):
    """Schema for a query suggestion"""
    question: str = Field(..., description="Suggested question")
    category: str = Field(..., description="Question category")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Suggestion confidence")
    examples: Optional[List[str]] = Field(
        None, description="Example follow-ups")


class QuerySuggestionsResponse(BaseModel):
    """Schema for query suggestions response"""
    video_id: str = Field(..., description="Video ID")
    suggestions: List[QuerySuggestion] = Field(
        ..., description="List of suggestions")
    total_suggestions: int = Field(...,
                                   description="Total number of suggestions")
    categories: List[str] = Field(..., description="Available categories")

# Query templates


class QueryTemplate(BaseModel):
    """Schema for a query template"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template: str = Field(..., description="Query template with variables")
    variables: List[Dict[str, str]
                    ] = Field(..., description="Template variables")
    category: str = Field(..., description="Template category")
    usage_count: int = Field(default=0, description="Number of times used")


class QueryTemplatesResponse(BaseModel):
    """Schema for query templates response"""
    templates: List[QueryTemplate] = Field(...,
                                           description="List of templates")
    total_templates: int = Field(..., description="Total number of templates")
    categories: List[str] = Field(..., description="Available categories")
