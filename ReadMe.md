# 👁️ Visi-Agent: Multimodal Video Analytics RAG

**Visi-Agent** is an Agentic AI system that enables natural language querying of video content. By synchronizing visual frame descriptions with audio transcripts, it allows users to "talk" to their videos and retrieve specific time-stamped information.

---

## 🚀 Getting Started

### 1. Installation & Setup
Clone the repository and install the dependencies defined in the `pyproject.toml`.

```bash
# Clone the repository
git clone https://github.com/ChethanPutran/Visi-Agent.git
cd Visi-Agent

# Navigate to your local project path
cd /video_analytics

# Set up virtual environment
python -m venv venv
source venv/bin/activate
pip install .
```

### 2. Configuration
Create a `.env` file in the root directory and add your API credentials:
```env
GEMINI_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_ENV=your_environment_here
LLM_MODEL=your_gemini_model_here
```

---

## 🛠️ Running the Application

### Step 1: Start the Backend (FastAPI)
The backend manages the video processing pipeline (Whisper + Vision) and the Pinecone vector index.
```bash
# From the project root
video-api
```

### Step 2: Start the Frontend
The UI is built with Streamlit. Run it from the `frontend/` directory:
```bash
cd frontend
python app.py
```
> **Access:** Open your browser and go to `http://localhost:5000`

---

## 🌐 API Reference

### Video Processing
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/videos/upload` | Upload a video file |
| `POST` | `/api/v1/videos/{id}/process` | Trigger Vision + Whisper indexing |
| `GET` | `/api/v1/videos/{id}/status` | Check ingestion progress |
| `GET` | `/api/v1/videos/{id}/transcript` | Retrieve synced audio data |
| `GET` | `/api/v1/videos/list` | List all processed videos |

### Queries
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/queries/ask` | Ask a natural language question |
| `GET` | `/api/v1/queries/history/{id}` | View query history for a video |

---

## 🏗️ Technical Architecture

* **Temporal Ingestion:** Syncs audio transcripts with visual frame descriptions for precise retrieval.
* **Agentic Search:** Uses LangChain tools to intelligently query time-stamped data.
* **MCP Ready:** Implements the Model Context Protocol to act as a plugin for Claude or other LLM hosts.
* **Multimodal Context:** Combines OpenAI Whisper (STT) and Vision-LLM outputs (Gemini 1.5 Flash).

---

##  Folder Structure

```
└── 📁src
    └── 📁services
        └── 📁api_gateway
            └── 📁app
                └── 📁dependencies
                    ├── services.py
                └── 📁middleware
                    ├── auth.py
                    ├── logging.py
                    ├── rate_limit.py
                └── 📁routes
                    ├── config_routes.py
                    ├── health_routes.py
                    ├── home_routes.py
                    ├── query_routes.py
                    ├── video_routes.py
                └── 📁schemas
                    ├── response_schemas.py
                    ├── video_schemas.py
                ├── main.py
        └── 📁llm_service
            └── 📁app
                └── 📁agent
                    └── 📁core
                        ├── video_agent.py
                    └── 📁memory
                        ├── local_memory.py
                    └── 📁prompts
                        ├── __init__.py
                        ├── agent_prompt.py
                        ├── chat.py
                        ├── video_desc.py
                        ├── video_summary.py
                    └── 📁tools
                        ├── __init__.py
                        ├── test.py
                        ├── video_search.py
                    ├── __init__.py
                    ├── test.py
                └── 📁contacts
                ├── llm_service.py
        └── 📁query_services
            └── 📁app
                └── 📁contracts
                    ├── __init__.py
                    ├── query_schemas.py
                └── 📁domain
                └── 📁handlers
                    ├── query_service.py
                └── 📁retrievers
        └── 📁session_service
            └── 📁app
                └── 📁adapters
                └── 📁domain
                └── 📁handlers
        └── 📁video_ingestion
            └── 📁app
                └── 📁contracts
                    ├── schemas.py
                └── 📁domain
                └── 📁handlers
                    ├── video_service.py
                └── 📁repositories
        └── 📁video_processing
            └── 📁app
                └── 📁contracts
                    ├── schemas.py
                └── 📁processors
                    └── 📁audio
                        ├── transcriber.py
                    └── 📁text
                        ├── summarizer.py
                    └── 📁vision
                        ├── frame_analyzer.py
                        ├── interfaces.py
                    ├── video_pipeline.py
                └── 📁workers
    └── 📁shared
        └── 📁config
            ├── logging_config.py
            ├── mcp_config.json
            ├── settings.py
        └── 📁contracts
            ├── video_metadata.py
        └── 📁logging
            ├── logger.py
        └── 📁messaging
        └── 📁storage
            └── 📁base
                ├── __init__.py
                ├── base_cache.py
                ├── base_queue.py
                ├── base_storage.py
                ├── base_vector_store.py
            └── 📁factories
                ├── __init__.py
                ├── blob_storage_service.py
                ├── cache_storage_service.py
                ├── queue_service.py
                ├── vector_storage_service.py
            └── 📁providers
                └── 📁blobs
                    ├── __init__.py
                    ├── local_storage.py
                    ├── s3_provider.py
                └── 📁cache
                    ├── __init__.py
                    ├── local_cache.py
                    ├── redis_cache.py
                └── 📁queue
                    ├── __init__.py
                    ├── local_queue.py
                    ├── redis_queue.py
                └── 📁vector
                    ├── __init__.py
                    ├── chroma_provider.py
                    ├── faiss_provider.py
                    ├── pinecone_provider.py
                ├── __init__.py
            └── 📁repository
                ├── __init__.py
                ├── chat_repository.py
                ├── video_repository.py
    ├── __init__.py
    └── main.py
```
---