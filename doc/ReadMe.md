# VideoMind MCP: Semantic Video Intelligence

**VideoMind** is a production-grade Model Context Protocol (MCP) server that empowers LLMs to "see," "hear," and "understand" video content through a structured semantic index. By transforming unstructured video streams into a queryable temporal knowledge base, VideoMind allows AI agents to perform complex reasoning across visual, auditory, and textual dimensions.

## Core Architecture

### 1. Multimodal Extraction Pipeline

Our pipeline decomposes video into a rich JSON schema using state-of-the-art models:

* **Visual Intelligence:** Frame-level captioning and scene description via **InternVL2** or **BLIP-2**.
* **Textual Perception:** High-fidelity OCR for on-screen text and slide content using **Tesseract**.
* **Auditory Intelligence:** Zero-latency ASR (Speech-to-Text) and speaker diarization using **OpenAI Whisper** + **Pyannote.audio**.

### 2. Temporal Semantic Indexing

Unlike standard RAG, VideoMind uses a **Temporal-Semantic Chunking** strategy:

* **Hybrid Search:** Combines dense vector embeddings (Milvus/Weaviate) with metadata filters.
* **Contextual Windows:** Overlapping temporal chunks ensure the LLM understands the "before" and "after" of a specific timestamp.

---

## MCP Tools & Integration

VideoMind exposes specialized tools that allow any MCP-compliant client (like Claude Desktop or custom agents) to interact with video data:

| Tool | Parameters | Description |
| --- | --- | --- |
| `search_video` | `query`, `time_range`, `limit` | Performs hybrid semantic search to find specific moments (e.g., "Where is gradient descent explained?") |
| `summarize_segment` | `start_t`, `end_t` | Aggregates visual captions and transcripts into a concise temporal summary. |
| `get_visual_context` | `timestamp` | Retrieves the specific OCR and frame descriptions for a precise moment. |

---

## Transport Layers

VideoMind is designed for flexible deployment:

* **stdio:** Optimized for local integration with desktop LLM clients.
* **SSE (Server-Sent Events):** Built for remote, scalable cloud deployments and web-based AI interfaces.


> **Example Query:**
> *"Find the section where the speaker discusses the backpropagation algorithm, then summarize the slide visible at that time."*

---
