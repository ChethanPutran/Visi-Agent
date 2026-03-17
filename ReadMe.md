### Folder structure
```python
video-analytics-system/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── main.py                          # Main entry point
├── config/                          # Configuration files
│   ├── __init__.py
│   ├── settings.py                  # App settings
│   ├── mcp_config.json              # MCP server config
│   └── logging_config.py            # Logging configuration
├── src/                             # Main source code
│   ├── __init__.py
│   ├── backend/                     # Backend/API layer
│   │   ├── __init__.py
│   │   ├── api/                     # FastAPI endpoints
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── video_routes.py  # Video-related endpoints
│   │   │   │   ├── query_routes.py  # Query endpoints
│   │   │   │   └── health_routes.py # Health/status endpoints
│   │   │   ├── middleware/          # API middleware
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py          # Authentication middleware
│   │   │   │   └── logging.py       # Request logging
│   │   │   └── schemas/             # Pydantic schemas
│   │   │       ├── __init__.py
│   │   │       ├── video_schemas.py
│   │   │       ├── query_schemas.py
│   │   │       └── response_schemas.py
│   │   ├── services/                # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── video_service.py     # Video processing service
│   │   │   ├── query_service.py     # Query handling service
│   │   │   ├── storage_service.py   # Storage management
│   │   │   └── cache_service.py     # Caching layer
│   │   └── models/                  # Database models
│   │       ├── __init__.py
│   │       ├── video_model.py       # Video metadata model
│   │       ├── analysis_model.py    # Analysis results model
│   │       └── user_model.py        # User model (if needed)
│   ├── agent/                       # AI Agent layer
│   │   ├── __init__.py
│   │   ├── core/                    # Agent core components
│   │   │   ├── __init__.py
│   │   │   ├── agent_executor.py    # Main agent executor
│   │   │   ├── tool_registry.py     # Tool registration & management
│   │   │   └── memory_manager.py    # Conversation memory
│   │   ├── tools/                   # Agent tools
│   │   │   ├── __init__.py
│   │   │   ├── video_tools.py       # Video-specific tools
│   │   │   ├── search_tools.py      # Search tools
│   │   │   ├── analysis_tools.py    # Analysis tools
│   │   │   └── utils_tools.py       # Utility tools
│   │   ├── prompts/                 # Prompt templates
│   │   │   ├── __init__.py
│   │   │   ├── query_prompts.py
│   │   │   ├── summary_prompts.py
│   │   │   └── analysis_prompts.py
│   │   └── mcp/                     # MCP server implementation
│   │       ├── __init__.py
│   │       ├── mcp_server.py        # MCP server
│   │       ├── mcp_tools.py         # MCP tool definitions
│   │       └── mcp_handlers.py      # MCP request handlers
│   ├── pipelines/                   # Processing pipelines
│   │   ├── __init__.py
│   │   ├── video_pipeline.py        # Main video processing pipeline
│   │   ├── stages/                  # Pipeline stages
│   │   │   ├── __init__.py
│   │   │   ├── audio_stage.py       # Audio extraction & processing
│   │   │   ├── transcription_stage.py # Whisper transcription
│   │   │   ├── vision_stage.py      # Visual analysis
│   │   │   ├── summary_stage.py     # Summary generation
│   │   │   └── indexing_stage.py    # Vector indexing
│   │   ├── orchestrators/           # Pipeline orchestration
│   │   │   ├── __init__.py
│   │   │   ├── base_orchestrator.py
│   │   │   ├── async_orchestrator.py
│   │   │   └── batch_orchestrator.py
│   │   └── utils/                   # Pipeline utilities
│   │       ├── __init__.py
│   │       ├── ffmpeg_utils.py      # FFmpeg utilities
│   │       ├── frame_utils.py       # Frame processing utilities
│   │       └── time_utils.py        # Time manipulation utilities
│   ├── processing/                  # Core processing modules
│   │   ├── __init__.py
│   │   ├── audio/                   # Audio processing
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py         # Audio extraction
│   │   │   ├── transcriber.py       # Whisper transcription
│   │   │   └── processor.py         # Audio processing utilities
│   │   ├── vision/                  # Vision processing
│   │   │   ├── __init__.py
│   │   │   ├── frame_extractor.py   # Frame extraction
│   │   │   ├── vision_analyzer.py   # GPT-4 Vision analysis
│   │   │   ├── object_detector.py   # Object detection (optional)
│   │   │   └── scene_analyzer.py    # Scene analysis
│   │   ├── text/                    # Text processing
│   │   │   ├── __init__.py
│   │   │   ├── summarizer.py        # Text summarization
│   │   │   ├── chunker.py           # Text chunking
│   │   │   └── embedding_generator.py # Text embeddings
│   │   └── vector_store/            # Vector storage
│   │       ├── __init__.py
│   │       ├── base_store.py        # Base vector store interface
│   │       ├── faiss_store.py       # FAISS implementation
│   │       ├── pinecone_store.py    # Pinecone implementation
│   │       └── chroma_store.py      # ChromaDB implementation
│   └── utils/                       # Shared utilities
│       ├── __init__.py
│       ├── logger.py                # Logging utilities
│       ├── file_utils.py            # File operations
│       ├── video_utils.py           # Video utilities
│       ├── api_utils.py             # API client utilities
│       └── validation.py            # Input validation
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_backend.py
│   │   ├── test_agent.py
│   │   └── test_pipelines.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_api_integration.py
│   │   └── test_agent_integration.py
│   └── fixtures/                    # Test fixtures
│       ├── __init__.py
│       ├── sample_videos.py
│       └── mock_responses.py
├── data/                            # Data storage
│   ├── videos/                      # Original videos (input)
│   │   └── .gitkeep
│   ├── processed/                   # Processed videos
│   │   └── .gitkeep
│   ├── transcripts/                 # Transcript files
│   │   └── .gitkeep
│   ├── summaries/                   # Summary files
│   │   └── .gitkeep
│   ├── indices/                     # Vector indices
│   │   └── .gitkeep
│   └── cache/                       # Cache files
│       └── .gitkeep
├── storage/                         # Persistent storage (optional)
│   ├── models/                      # ML models
│   │   └── whisper/                 # Whisper models
│   └── embeddings/                  # Embedding models
├── scripts/                         # Utility scripts
│   ├── setup.sh                     # Setup script
│   ├── run_mcp.sh                   # MCP server script
│   ├── run_api.sh                   # API server script
│   ├── process_batch.py             # Batch processing script
│   └── migrate_data.py              # Data migration script
├── docs/                            # Documentation
│   ├── api.md                       # API documentation
│   ├── agent.md                     # Agent documentation
│   ├── pipelines.md                 # Pipelines documentation
│   └── deployment.md                # Deployment guide
└── examples/                        # Example usage
    ├── __init__.py
    ├── basic_usage.py               # Basic usage example
    ├── mcp_client.py                # MCP client example
    ├── api_client.py                # API client example
    └── batch_processing.py          # Batch processing example

src/
  services/
    api_gateway/
      app/
        main.py
        routes/
        schemas/
        dependencies/
    video_ingestion/
      app/
        handlers/
        domain/
        repositories/
        contracts/
    video_processing/
      app/
        workers/
        domain/
        processors/
          audio/
          vision/
          text/
        contracts/
    query_service/
      app/
        handlers/
        domain/
        retrievers/
        contracts/
    session_service/
      app/
        handlers/
        domain/
        adapters/
  shared/
    contracts/        # Pydantic DTOs/events only
    config/
    logging/
    storage/
    messaging/

```

    
# Visi-Agent: Multimodal Video Analytics RAG

A Agentic AI system that enables natural language querying of video content. 

## Features
- **Temporal Ingestion:** Syncs audio transcripts with visual frame descriptions.
- **Agentic Search:** Uses LangChain tools to perform similarity searches across time-stamped data.
- **MCP Ready:** Implements the Model Context Protocol to act as a plugin for Claude or other LLM hosts.
- **Multimodal Context:** Combines Whisper (speech-to-text) and Vision-LLM outputs.

## Installation
1. Clone the repo.
2. Install dependencies:
   ```bash
   pip install opencv-python openai-whisper pinecone-client langchain-openai moviepy mcp



3. Set your environment variables:
`OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_ENV`.

## Usage

1. **Ingest:** Run `python ingest.py --file video.mp4` to process and index.
2. **Query:** Run `python agent.py` to ask questions about the video.
3. **MCP Server:** Start the server using `python mcp_server.py`.

### Routes
1. Video processing routes
https://localhost:8000/api/v1/videos/upload
https://localhost:8000/api/v1/videos/{video_id}/status
https://localhost:8000/api/v1/videos/{video_id}/process
https://localhost:8000/api/v1/videos/{video_id}/trascript
https://localhost:8000/api/v1/videos/{video_id}/summary
https://localhost:8000/api/v1/videos/{video_id}
https://localhost:8000/api/v1/videos/list

2. Querry processing routes
3. General routes