## 🏗️ Architecture: Multimodal Video RAG Agent

### 1. Project Overview

This project, **Visi-Agent**, is an AI-powered video analytics engine. It processes video files by "seeing" (frame analysis) and "hearing" (transcription), indexes this data into a vector store, and exposes it through a **Model Context Protocol (MCP)** server for agentic interaction.

### 2. Tech Stack

* **Orchestration:** LangChain / LangGraph
* **Video Processing:** OpenCV (Frames), OpenAI Whisper (Audio)
* **Vision-Language Model:** GPT-4o (for frame description)
* **Vector Database:** Pinecone (Serverless)
* **Agent Interface:** Model Context Protocol (MCP)
