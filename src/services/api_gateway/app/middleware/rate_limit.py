import time
from fastapi import Request, HTTPException
from collections import defaultdict
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.requests[client_ip].append(now)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)

async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware
    """
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again in a minute."
        )
    
    return await call_next(request)