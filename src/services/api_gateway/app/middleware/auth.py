from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

from src.shared.logging.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

async def verify_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None
):
    """
    Verify API key from header or query parameter
    """
    # Get API key from environment
    valid_api_key = os.getenv("API_KEY")
    
    # If no API key is set, allow all requests (for development)
    if not valid_api_key:
        logger.warning("API_KEY not set, skipping authentication")
        return
    
    # Try to get API key from various sources
    api_key = None
    
    # 1. From Authorization header
    if credentials:
        api_key = credentials.credentials
    
    # 2. From query parameter
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    # 3. From X-API-Key header
    if not api_key:
        api_key = request.headers.get("x-api-key")
    
    if not api_key:
        logger.warning("No API key provided")
        raise HTTPException(
            status_code=401,
            detail="API key is required"
        )
    
    if api_key != valid_api_key:
        logger.warning(f"Invalid API key attempt from {request.client}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    logger.debug(f"API key validated for {request.client}")