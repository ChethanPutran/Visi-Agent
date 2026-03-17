from fastapi import APIRouter

from src.shared.config.settings import settings

router = APIRouter()

@router.get("/config")
async def get_config():
    """
    Get current configuration (for debugging, don't expose in production)
    """
    if settings.is_production:
        return {"message": "Configuration not available in production"}
    
    return {
        "environment": settings.APP_ENV,
        "debug": settings.DEBUG,
        "openai_available": settings.openai_available,
        "storage_type": settings.STORAGE_TYPE,
        "vector_db_type": settings.VECTOR_DB_TYPE
    }

@router.get("/storage-config")
async def get_storage_config():
    """
    Get storage configuration
    """
    return settings.get_storage_config()

@router.get("/vector-config")
async def get_vector_config():
    """
    Get vector database configuration
    """
    return settings.get_vector_db_config()