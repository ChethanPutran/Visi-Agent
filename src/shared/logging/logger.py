"""
Logger utility with structured logging
"""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from src.shared.config.settings import settings

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development"""
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        log_line = (
            f"{color}[{record.levelname:8}]{reset} "
            f"{record.name} - {record.module}.{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"
        
        return log_line

def setup_logging():
    """Setup logging configuration based on settings"""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.APP_ENV == "development":
        console_handler.setFormatter(ConsoleFormatter())
    else:
        console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler for errors
    error_handler = logging.FileHandler(
        logs_dir / "error.log",
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    logger.addHandler(error_handler)
    
    # File handler for all logs
    if settings.LOG_TO_FILE:
        file_handler = logging.FileHandler(
            logs_dir / "app.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # Suppress noisy logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # # Add extra fields capability
    # def make_record_with_extra(self, *args, **kwargs):
    #     rv = logging.Logger.makeRecord(self, *args, **kwargs)
    #     rv.extra = kwargs.get("extra", {})
    #     return rv
    
    # logger.makeRecord = make_record_with_extra.__get__(logger, logging.Logger)
    
    return logger

# Convenience functions
def log_with_context(logger: logging.Logger, level: str, msg: str, **kwargs):
    """Log with additional context"""
    extra = kwargs.pop('extra', {})
    context = {
        'timestamp': datetime.utcnow().isoformat(),
        **kwargs,
        **extra
    }
    
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(msg, extra={'extra': context})

def log_request(logger: logging.Logger, request_id: str, method: str, path: str, 
                client_ip: str, user_agent: str = ''):
    """Log HTTP request"""
    logger.info(
        f"Request {request_id}: {method} {path}",
        extra={
            'request_id': request_id,
            'method': method,
            'path': path,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'type': 'request'
        }
    )

def log_response(logger: logging.Logger, request_id: str, status_code: int, 
                 duration: float, error: str = ''):
    """Log HTTP response"""
    level = "error" if error or status_code >= 400 else "info"
    
    log_method = getattr(logger, level)
    log_method(
        f"Response {request_id}: {status_code} ({duration:.3f}s)",
        extra={
            'request_id': request_id,
            'status_code': status_code,
            'duration': duration,
            'error': error,
            'type': 'response'
        }
    )