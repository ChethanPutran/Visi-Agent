"""
Logging configuration for the application
"""
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any
import json

from .settings import settings

def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration based on settings
    """
    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.LOG_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": json.dumps({
                    "timestamp": "%(asctime)s",
                    "name": "%(name)s",
                    "level": "%(levelname)s",
                    "message": "%(message)s",
                    "module": "%(module)s",
                    "function": "%(funcName)s",
                    "line": "%(lineno)d",
                    "process": "%(process)d",
                    "thread": "%(thread)d"
                }),
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL.upper(),
                "formatter": "default",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": settings.LOG_LEVEL.upper(),
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "fastapi": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    
    # Add file handler if LOG_FILE is configured
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        base_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL.upper(),
            "formatter": "default" if settings.is_development else "json",
            "filename": str(log_path),
            "maxBytes": settings.LOG_MAX_SIZE,
            "backupCount": settings.LOG_BACKUP_COUNT,
            "encoding": "utf-8"
        }
        
        # Add file handler to root logger
        base_config["loggers"][""]["handlers"].append("file")
    
    return base_config

def setup_logging():
    """
    Setup logging configuration
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Set third-party loggers
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}")
    logger.info(f"Application environment: {settings.APP_ENV}")
    
    if settings.is_development:
        logger.info("Running in development mode")
    elif settings.is_production:
        logger.info("Running in production mode")