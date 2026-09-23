# Visi-Agent

### Agentic Multimodal Video Analytics & Retrieval

Visi-Agent is an **agentic AI system for querying video using natural language**.

It transforms unstructured video into a searchable multimodal representation by combining **speech transcription, visual frame analysis, temporal alignment, vector retrieval, and LLM-based reasoning**. Users can upload a video and ask questions about what happened, when it happened, and what was said or shown.

> **Ask questions about your videos instead of manually searching through them.**

---

## ✨ Overview

Traditional video search is mostly keyword-based and often requires manually scanning the timeline.

Visi-Agent approaches video understanding as a **multimodal retrieval and reasoning problem**.

A video is processed into temporally aligned information from multiple modalities:

* 🎙️ **Audio** → speech transcription using Whisper
* 👁️ **Vision** → sampled video frames and visual descriptions
* ⏱️ **Temporal Context** → timestamps connecting events across modalities
* 🧠 **Embeddings** → vector representations for semantic retrieval
* 🔎 **Retrieval** → similarity-based search over video content
* 🤖 **Agentic Reasoning** → LLM tools for search and temporal analysis
* 💬 **Conversation** → contextual follow-up questions about the video

This allows queries such as:

```text
"What happened when the speaker mentioned the project?"

"When did the car enter the scene?"

"Summarize the discussion about the database."

"What happened immediately after the person entered the room?"

"Find the part of the video where they discuss the deployment architecture."
```

---

## 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │       User          │
                         │ Natural Language    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Flask Frontend   │
                         │   Web Interface     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    FastAPI Gateway  │
                         │  REST API / Routing │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
                  ▼                                   ▼
        ┌──────────────────┐                ┌──────────────────┐
        │ Video Ingestion  │                │  Query Service   │
        │     Service      │                │                  │
        └────────┬─────────┘                └────────┬─────────┘
                 │                                   │
                 ▼                                   │
        ┌──────────────────┐                         │
        │ Video Processing │                         │
        │     Pipeline     │                         │
        └────────┬─────────┘                         │
                 │                                   │
        ┌────────┴─────────┐                         │
        │                  │                         │
        ▼                  ▼                         │
 ┌─────────────┐    ┌──────────────┐                │
 │   Whisper   │    │ Vision /     │                │
 │ Transcriber │    │ Frame        │                │
 │             │    │ Analysis     │                │
 └──────┬──────┘    └──────┬───────┘                │
        │                  │                         │
        └────────┬─────────┘                         │
                 ▼                                   │
        ┌──────────────────┐                         │
        │ Temporal          │                         │
        │ Multimodal Data   │                         │
        └────────┬─────────┘                         │
                 │                                   │
                 ▼                                   │
        ┌──────────────────┐                         │
        │ Vector Storage   │◄────────────────────────┘
        │ FAISS / Chroma / │
        │ Pinecone / ...   │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Video Analytics  │
        │ Agent            │
        │                  │
        │ Search Tool      │
        │ Temporal Tool    │
        │ LLM Reasoning    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Timestamp-aware  │
        │ Answer           │
        └──────────────────┘
```

---

## 🔄 Processing Pipeline

### 1. Video Upload

A user uploads a video through the application.

The ingestion layer stores the video and creates metadata required for subsequent processing.

### 2. Audio Extraction

Audio is extracted from the video using **FFmpeg**.

```text
Video
  │
  └──► FFmpeg
          │
          └──► Audio
```

### 3. Speech Transcription

The extracted audio is processed using **OpenAI Whisper** to generate timestamped transcript segments.

Example:

```json
{
  "start": 42.3,
  "end": 47.8,
  "text": "We will deploy the service using Kubernetes."
}
```

### 4. Visual Processing

Video frames are sampled at configurable intervals.

The system associates frames with corresponding temporal segments of the transcript, creating a multimodal representation of the video.

```text
Video Timeline

0s ─────── 10s ─────── 20s ─────── 30s
          │             │
       Transcript    Visual Frames
          │             │
          └──────┬──────┘
                 ▼
        Temporal Context
```

### 5. Multimodal Representation

Each temporal segment can contain information from multiple sources:

```text
Temporal Segment
│
├── Transcript
│
├── Visual Frames
│
├── Visual Description
│
└── Timestamp
```

This provides the retrieval layer with both **what was said** and **what was visible**.

### 6. Vector Retrieval

Semantic representations are stored using a vector-store abstraction.

The repository currently includes implementations for:

* FAISS
* Chroma
* Pinecone

This abstraction makes it possible to change the vector backend without rewriting the application-level retrieval logic.

### 7. Agentic Querying

The video agent uses an LLM together with tools for interacting with the indexed video.

Current agent capabilities include:

* **Video search**
* **Temporal analysis**
* **Conversational querying**

Instead of simply performing one vector lookup, the agent can decide when to search the video and when to perform temporal reasoning over retrieved events.

### 8. Answer Generation

Retrieved information is passed to the LLM to generate a natural-language response.

The goal is to preserve the relationship between the answer and the original video timeline.

---

## 🧠 Agent Architecture

The core video agent is built around LangChain's agent/tool abstraction.

Conceptually:

```text
                     User Question
                           │
                           ▼
                    ┌─────────────┐
                    │     LLM     │
                    │    Agent    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌──────────────┐         ┌─────────────────┐
       │ Video Search │         │    Temporal     │
       │     Tool     │         │    Analysis     │
       └──────┬───────┘         └────────┬────────┘
              │                          │
              └───────────┬──────────────┘
                          ▼
                   Retrieved Context
                          │
                          ▼
                    Final Answer
```

The temporal analysis tool can perform multiple searches and combine events to reason about their chronological ordering.

---

## 🧩 Main Components

### API Gateway

The API gateway provides the external REST interface and coordinates the backend services.

Responsibilities include:

* Request routing
* Video endpoints
* Query endpoints
* Health checks
* Configuration
* Middleware
* Rate limiting
* Authentication hooks

### Video Ingestion Service

Responsible for accepting and managing uploaded videos.

### Video Processing Service

Coordinates the multimodal processing pipeline:

* Audio extraction
* Whisper transcription
* Frame sampling
* Visual analysis
* Summarization
* Embedding generation

### LLM Service

Provides the LLM-powered capabilities used by the application and video agent.

### Query Service

Handles natural-language queries, conversation history, and interaction with the LLM layer.

### Storage Layer

The project uses provider abstractions for:

* Object/blob storage
* Caching
* Queues
* Vector databases

This allows infrastructure implementations to be changed without tightly coupling the application to a single provider.

---

## 🛠️ Technology Stack

| Layer                  | Technology                                 |
| ---------------------- | ------------------------------------------ |
| Language               | Python                                     |
| API                    | FastAPI                                    |
| Frontend               | Flask                                      |
| Agent Framework        | LangChain                                  |
| LLM                    | Google Gemini                              |
| Speech-to-Text         | OpenAI Whisper                             |
| Video Processing       | OpenCV                                     |
| Video/Audio Processing | FFmpeg                                     |
| Embeddings             | CLIP / configurable vector representations |
| Vector Stores          | FAISS, Chroma, Pinecone                    |
| Cache                  | Local / Redis                              |
| Queue                  | Local / Redis                              |
| Object Storage         | Local / S3-compatible                      |
| Protocol               | Model Context Protocol (MCP)               |
| Validation             | Pydantic                                   |
| Testing                | Pytest                                     |
| Containerization       | Docker                                     |

---

## 📁 Project Structure

```text
Visi-Agent/
│
├── frontend/
│   └── app.py
│
├── src/
│   │
│   ├── services/
│   │   │
│   │   ├── api_gateway/
│   │   │   └── app/
│   │   │       ├── middleware/
│   │   │       ├── routes/
│   │   │       └── schemas/
│   │   │
│   │   ├── video_ingestion/
│   │   │   └── app/
│   │   │
│   │   ├── video_processing/
│   │   │   └── app/
│   │   │       ├── processors/
│   │   │       │   ├── audio/
│   │   │       │   ├── vision/
│   │   │       │   └── text/
│   │   │       └── workers/
│   │   │
│   │   ├── llm_service/
│   │   │   └── app/
│   │   │       ├── agent/
│   │   │       ├── prompts/
│   │   │       └── tools/
│   │   │
│   │   ├── query_services/
│   │   │   └── app/
│   │   │
│   │   └── session_service/
│   │       └── app/
│   │
│   ├── shared/
│   │   ├── config/
│   │   ├── contracts/
│   │   ├── logging/
│   │   ├── messaging/
│   │   └── storage/
│   │       ├── base/
│   │       ├── factories/
│   │       ├── providers/
│   │       └── repository/
│   │
│   └── main.py
│
├── tests/
├── scripts/
├── data/
├── logs/
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

Make sure the following are installed:

* Python 3.10+
* FFmpeg
* Git
* An LLM API key
* Optional: Pinecone credentials if using Pinecone
* Optional: CUDA-enabled GPU for faster Whisper inference

### 1. Clone the repository

```bash
git clone https://github.com/ChethanPutran/Visi-Agent.git
cd Visi-Agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install the project

```bash
pip install .
```

For development/testing dependencies:

```bash
pip install ".[test]"
```

### 4. Install FFmpeg

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

### 5. Configure environment variables

Create an environment configuration file appropriate for your environment, for example:

```text
.env.development
```

Example:

```env
APP_ENV=development

GEMINI_API_KEY=your_gemini_api_key

VECTOR_PROVIDER=faiss
VECTOR_DB_PATH=./data/vectors

WHISPER_MODEL=base

LLM_MODEL=gemini-3-flash-preview

VISION_ENABLED=true
VISION_FRAME_INTERVAL=2
VISION_BATCH_SIZE=5
```

If using Pinecone:

```env
VECTOR_PROVIDER=pinecone

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=your_index
```

---

## ▶️ Running the Application

### Start the backend

The project exposes a `video-api` command through `pyproject.toml`.

```bash
video-api
```

The API runs on:

```text
http://localhost:8000
```

FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

### Start the frontend

```bash
cd frontend
python app.py
```

The frontend runs on:

```text
http://localhost:5000
```

---

## 🔌 API

### Video Processing

| Method | Endpoint                         | Purpose                 |
| ------ | -------------------------------- | ----------------------- |
| `POST` | `/api/v1/videos/upload`          | Upload a video          |
| `POST` | `/api/v1/videos/{id}/process`    | Start video processing  |
| `GET`  | `/api/v1/videos/{id}/status`     | Check processing status |
| `GET`  | `/api/v1/videos/{id}/transcript` | Retrieve transcript     |
| `GET`  | `/api/v1/videos/list`            | List processed videos   |

### Querying

| Method | Endpoint                       | Purpose                       |
| ------ | ------------------------------ | ----------------------------- |
| `POST` | `/api/v1/queries/ask`          | Ask a question about a video  |
| `GET`  | `/api/v1/queries/history/{id}` | Retrieve conversation history |

---

## 💬 Example Workflow

```text
1. Upload video
       │
       ▼
2. Extract audio
       │
       ▼
3. Generate Whisper transcript
       │
       ├──────────────┐
       │              │
       ▼              ▼
   Transcript     Sample Frames
       │              │
       │              ▼
       │        Visual Analysis
       │              │
       └───────┬──────┘
               ▼
       Temporal Multimodal
           Representation
               │
               ▼
          Vector Index
               │
               ▼
        User asks question
               │
               ▼
          Agent searches
               │
               ▼
        Temporal reasoning
               │
               ▼
          LLM response
               │
               ▼
      Timestamp-aware answer
```

---

## 🔬 Design Principles

### Multimodal Understanding

Video meaning is distributed across speech and visual information. Visi-Agent therefore treats these modalities as complementary rather than relying exclusively on transcripts.

### Temporal Grounding

Video queries are inherently time-dependent. Transcript segments and visual observations are associated with timestamps to preserve their relationship with the original video timeline.

### Agentic Retrieval

The system uses an LLM agent with specialized tools instead of treating retrieval as a single fixed search operation.

### Provider Abstraction

Storage, caching, queues, and vector databases are abstracted behind interfaces/providers, allowing infrastructure to be replaced without redesigning the higher-level services.

### Service Separation

Video ingestion, processing, querying, LLM interaction, and API routing are separated into independent service boundaries.

---

## 🧪 Testing

Run the test suite with:

```bash
pytest
```

The project also provides optional testing dependencies through:

```bash
pip install ".[test]"
```

---

## 🐳 Docker

A Dockerfile is included for containerized deployment.

Build:

```bash
docker build -t visi-agent .
```

Run:

```bash
docker run --env-file .env.development -p 8000:8000 visi-agent
```

---

## 🔮 Future Improvements

Potential directions for extending Visi-Agent include:

* [ ] More advanced multimodal embeddings
* [ ] Better cross-modal retrieval
* [ ] Timestamp-grounded citations in responses
* [ ] Multi-video querying
* [ ] Temporal range queries
* [ ] Video-to-video comparison
* [ ] Query suggestions
* [ ] Improved asynchronous/background processing
* [ ] Distributed task queues
* [ ] Streaming video ingestion
* [ ] Authentication and authorization
* [ ] Production observability
* [ ] Evaluation benchmarks for video retrieval and QA
* [ ] More vision-language model providers

---

## 📌 Current Status

Visi-Agent is an actively developed project exploring **agentic multimodal video understanding, temporal retrieval, and video question answering**.

The repository currently contains the core architecture for:

* Video ingestion
* Audio transcription
* Visual frame processing
* LLM-based analysis
* Vector retrieval
* Agentic querying
* Conversational interaction
* Pluggable storage infrastructure

Some advanced query and analytics capabilities remain under development.

---

## 🤝 Contributing

Contributions, ideas, and improvements are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/my-feature
```

3. Make your changes
4. Run the tests

```bash
pytest
```

5. Commit your changes

```bash
git commit -m "Add my feature"
```

6. Push the branch

```bash
git push origin feature/my-feature
```

7. Open a pull request

---

## 📄 License

MIT License

