from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
import psutil
import os
from datetime import datetime

from src.shared.config.settings import settings
from src.services.video_ingestion.app.handlers.video_service import VideoService
from src.services.query_services.app.handlers.query_service import QueryService
from src.shared.logging.logger import get_logger
from src.services.api_gateway.app.dependencies.services import (
    get_video_service,
    get_query_service,
)

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "video-analytics-api",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(
    video_service: VideoService = Depends(get_video_service),
    query_service: QueryService = Depends(get_query_service)
):
    """
    Detailed health check with service status
    """
    try:
        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check services
        video_service_status = await video_service.health_check()
        query_service_status = await query_service.health_check()
        
        # Check environment
        env_vars = {
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "APP_ENV": settings.APP_ENV,
            "STORAGE_TYPE": settings.STORAGE_TYPE
        }
        
        # Overall status
        all_healthy = all([
            video_service_status["healthy"],
            query_service_status["healthy"],
            cpu_percent < 90,
            memory.percent < 90
        ])
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "services": {
                "video_service": video_service_status,
                "query_service": query_service_status
            },
            "environment": env_vars,
            "settings": {
                "app_env": settings.APP_ENV,
                "app_host": settings.APP_HOST,
                "app_port": settings.APP_PORT,
                "log_level": settings.LOG_LEVEL
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/metrics")
async def get_metrics():
    """
    Get system and application metrics
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        # Network metrics
        net_io = psutil.net_io_counters()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu": {
                    "percent_per_core": cpu_percent,
                    "percent_total": sum(cpu_percent) / len(cpu_percent)
                },
                "memory": {
                    "percent": memory.percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2)
                }
            },
            "process": {
                "memory_rss_mb": round(process_memory.rss / (1024**2), 2),
                "memory_vms_mb": round(process_memory.vms / (1024**2), 2),
                "cpu_percent": process.cpu_percent(interval=1),
                "threads": process.num_threads(),
                "connections": len(process.connections())
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version")
async def get_version():
    """
    Get API version information
    """
    return {
        "name": "Video Analytics API",
        "version": "1.0.0",
        "description": "AI-powered video processing and analysis API",
        "repository": "https://github.com/yourusername/video-analytics",
        "license": "MIT",
        "authors": ["Your Name <your.email@example.com>"],
        "documentation": "/docs"
    }

# @router.get("/endpoints")
# async def list_endpoints():
#     """
#     List all available API endpoints
#     """
#     from src.backend.api import create_app
#     app = create_app()
    
#     endpoints = []
#     for route in app.routes:
#         if hasattr(route, "methods"):
#             endpoints.append({
#                 "path": route.path,
#                 "methods": list(route.methods),
#                 "name": getattr(route, "name", ""),
#                 "summary": getattr(route, "summary", ""),
#                 "description": getattr(route, "description", "")
#             })
    
#     return {
#         "count": len(endpoints),
#         "endpoints": sorted(endpoints, key=lambda x: x["path"])
#     }