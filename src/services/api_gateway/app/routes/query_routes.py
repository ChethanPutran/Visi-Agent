from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Any, Dict, List
from fastapi.templating import Jinja2Templates

from src.services.query_services.app.contracts.query_schemas import (
    VideoQueryRequest,
    VideoQueryResponse,
    TemporalQueryRequest,
    ComparativeQueryRequest,
    SearchQueryRequest,
)
from src.services.query_services.app.handlers.query_service import QueryService
from src.services.api_gateway.app.dependencies.services import get_query_service
from src.shared.logging.logger import get_logger

templates = Jinja2Templates(directory="src/backend/api/templates")

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "query.html",
        {"request": request}
    )


@router.get("/history/{video_id}")
async def get_chat_history(
     video_id: str,
     query_service: QueryService = Depends(get_query_service)
    ):
    try:
        logger.info(f"Fetching chat history for video {video_id}")
        history = await query_service.get_chat_history(video_id)
        return {
            "video_id": video_id,
            "history": history
        }
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))     
    

@router.post("/ask", response_model=VideoQueryResponse)
async def ask_video_question(
    request: VideoQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Ask a natural language question about a video

    Example questions:
    - "What are the main topics discussed in the video?"
    - "When does the car appear and what color is it?"
    - "What did the speaker say about climate change?"
    """
    try:
        logger.info(
            f"Processing question for video {request.video_id}: {request.question}")

        result = await query_service.ask_question(
            video_id=request.video_id,
            question=request.question,
            include_timestamps=request.include_timestamps,
            max_results=request.max_results
        )
        query_type = request.query_type

       # Assuming 'result' contains the data you mentioned in the error
        return VideoQueryResponse(
            success=True,
            video_id=request.video_id,
            question=request.question or str(query_type),
            answer=result["answer"],
            
            # FIX: Extract the float from the dict (e.g., getting the 'start' time)
            # If your model expects a list of floats:
            timestamps=[t['start'] if isinstance(t, dict) else t for t in result.get("timestamps", [0.0])],
            
            confidence=result.get("confidence", 0.0),
            
            # FIX: Wrap the string into a dictionary to satisfy the 'dict_type' requirement
            sources=[{"segment_id": s} if isinstance(s, str) else s for s in result.get("sources", [{}])]
        )

    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/temporal", response_model=VideoQueryResponse)
async def query_temporal_range(
    request: TemporalQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Query what happens in a specific timeframe
    """
    try:
        result = await query_service.query_temporal_range(
            video_id=request.video_id,
            start_time=request.start_time,
            end_time=request.end_time,
            detail_level=request.detail_level
        )

        return VideoQueryResponse(
            success=True,
            video_id=request.video_id,
            question=f"What happens between {request.start_time}s and {request.end_time}s?",
            answer=result["answer"],
            timestamps=result.get("timestamps", [0.0]),
            confidence=result.get("confidence", 1.0),
            sources=result.get("sources", [{}])
        )

    except Exception as e:
        logger.error(f"Error in temporal query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=VideoQueryResponse)
async def compare_timeframes(
    request: ComparativeQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Compare two different timeframes in a video
    """
    try:
        result = await query_service.compare_timeframes(
            video_id=request.video_id,
            timeframe1=request.timeframe1,
            timeframe2=request.timeframe2
        )

        return VideoQueryResponse(
            success=True,
            video_id=request.video_id,
            question=f"Compare timeframe {request.timeframe1} with {request.timeframe2}",
            answer=result["answer"],
            timestamps=result.get("timestamps", []),
            confidence=result.get("confidence", 0.0),
            sources=[]
        )

    except Exception as e:
        logger.error(f"Error in comparison query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[Dict[str, Any]])
async def search_video_content(
    request: SearchQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Search for specific content in a video
    """
    try:
        results = await query_service.search_content(
            video_id=request.video_id,
            query=request.query,
            search_type=request.search_type,
            limit=request.max_results,
            threshold=request.confidence_threshold
        )

        return results

    except Exception as e:
        logger.error(f"Error searching content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/suggestions")
async def get_query_suggestions(
    video_id: str,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Get suggested questions for a video
    """
    try:
        suggestions = await query_service.get_query_suggestions(video_id)

        return {
            "video_id": video_id,
            "suggestions": suggestions
        }

    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-video")
async def query_multiple_videos(
    question: str,
    video_ids: List[str],
    query_service: QueryService = Depends(get_query_service)
):
    """
    Ask a question across multiple videos
    """
    try:
        result = await query_service.query_multiple_videos(
            video_ids=video_ids,
            question=question
        )

        return {
            "success": True,
            "question": question,
            "videos": video_ids,
            "answer": result["answer"],
            "per_video_answers": result.get("per_video_answers", {})
        }

    except Exception as e:
        logger.error(f"Error in multi-video query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
