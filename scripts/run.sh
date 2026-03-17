python video_analytics_mcp.py --http

# Development
export ENV_FILE=.env.development
python main.py

# Production
export ENV_FILE=.env.production
python main.py

# Or specify in command line
python main.py --config .env.production