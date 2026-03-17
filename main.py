import sys
import argparse
import os
import logging

def parse_api_args(args_to_parse):
    """Parse command-line arguments for API command."""
    parser = argparse.ArgumentParser(description="Run Video Analytics API")
    
    # We remove --command as a flag because you are using it as a positional sys.argv[1]
    parser.add_argument("--host", default=os.getenv("APP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("APP_PORT", 8000)))
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--workers", type=int, default=int(os.getenv("API_WORKERS", 4)))
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"]
    )
    # Pass the list explicitly here
    return parser.parse_args(args_to_parse)

def main():
    if len(sys.argv) > 1:
        args_list = sys.argv[1:]
        
        # Initialize logging early
        from src.shared.config.logging_config import setup_logging
        
        setup_logging()
        
        logger = logging.getLogger("main")
        api_args = parse_api_args(args_list)
        
        logger.debug(f"Starting API on {api_args.host}:{api_args.port}")

        # Run FastAPI server
        import uvicorn
 
        uvicorn.run(
        "src.services.api_gateway.app.main:app",
        host=api_args.host,
        port=api_args.port,
        reload=api_args.reload,
        reload_dirs=["src"],
        reload_excludes=[
            "logs/*", "data/*", "temp/*",
            "**/__pycache__/*", "*.pyc", ".pytest_cache/*", ".env*"
        ],
        log_level="info",
    )


    else:
        print("Usage: python main.py [api|mcp|process|worker] [args...]")
        print("Example: python main.py api --host 0.0.0.0 --port 8000 --reload")


if __name__ == "__main__":
    main()