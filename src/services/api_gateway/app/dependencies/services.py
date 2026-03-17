from fastapi import Request
from src.services.video_ingestion.app.handlers.video_service import VideoService
from src.services.query_services.app.handlers.query_service import QueryService

def get_video_service(request: Request) -> VideoService:
    return request.app.state.video_service

def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service
