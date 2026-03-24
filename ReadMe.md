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