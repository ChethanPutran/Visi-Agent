import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.shared.logging.logger import get_logger, log_request, log_response

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent") or "None"
        
        log_request(
            logger,
            request_id,
            request.method,
            str(request.url.path),
            client_ip,
            user_agent
        )
        
        try:
            # Process request
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log successful response
            log_response(
                logger,
                request_id,
                response.status_code,
                duration
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            log_response(
                logger,
                request_id,
                500,
                duration,
                error=str(e)
            )
            raise