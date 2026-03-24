import asyncio
import os
from typing import Dict, Any, List
from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from src.shared.config.settings import settings

from ..prompts import (
    agent_prompt,
    video_desc_extract_prompt_template,
    video_summary_prompt_template,
    chat_prompt
)
from src.services.llm_service.app.agent.tools.video_search import (
    initialize_video_search,
    get_video_summary as get_video_summary_tool,
    search_video_content as search_video_content_tool,
    find_temporal_sequence,
    analyze_visual_patterns
)
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class VideoAnalyticsAgent:
    """Main agent class for video analytics"""

    def __init__(self, model: str = settings.LLM_MODEL):
        """Initialize the LangChain agent with tools"""

        # 1. Determine and initialize the LLM first
        if "gemini" in model:
            self.llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=settings.LLM_TEMPERATURE,
                max_retries=settings.LLM_MAX_RETRIES,
                google_api_key=settings.GEMINI_API_KEY
            )
        elif model == "openai":
            # self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
            raise NotImplementedError("OpenAI support is not configured yet.")
        else:
            # Fallback or Error to ensure self.llm is never None
            raise ValueError(f"Unsupported model type: {model}")

        self.str_parser = StrOutputParser()

        # 3. Create chains (Now the "|" operator is safe because self.llm is guaranteed)
        self.frame_info_chain = video_desc_extract_prompt_template | self.llm | self.str_parser
        self.summary_chain = video_summary_prompt_template | self.llm | self.str_parser
        self.chat_chain = chat_prompt | self.llm | self.str_parser
        self.video_loaded = False
        self.video_metadata = {}
        self.processing_status = "idle"
        self.agent_executor = None
       
        self.str_parser = StrOutputParser()

        self.tools = [
            search_video_content_tool,
            get_video_summary_tool,
            find_temporal_sequence,
            analyze_visual_patterns
        ]

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=agent_prompt
        )

    async def chat(self, question:str, chat_history: List[Dict[str, Any]], video_id: str = None) -> Dict[str, Any]:
        """Chat with the agent, optionally in the context of a video"""
        try:
            response = await self.chat_chain.ainvoke({
                "history": chat_history,
                "question": question
            })
            return {
                "success": True,
                "answer": response,
                "video_id": video_id
            }
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            return {
                "success": False,
                "error": str(e),
                "video_id": video_id
            }
    def generate_video_summary(self, transcript_segments: List[Dict[str, Any]], frames_data: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive summary using transcript and visual data"""

        # Prepare combined context
        transcript_text = "\n".join([
            f"[{seg['start']:.1f}s-{seg['end']:.1f}s]: {seg['text']}"
            for seg in transcript_segments
        ])

        visual_context = "\n".join([
            f"[{frame['timestamp']:.1f}s]: {frame['description']}"
            for frame in frames_data
        ])

        try:
            response = self.summary_chain.invoke(
                {"transcript_text": transcript_text, "visual_context": visual_context})

            return response
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Summary generation failed."

    def analyze_frames_batch(self, frames_batch: List[Dict[str, Any]]) -> str:
        """Analyze multiple frames in a single batch for efficiency"""

        try:

            # Build the input text to include frames
            question = ""
            for frame in frames_batch:
                question += f"Timestamp: {frame['timestamp']} seconds.\n"
                question += f"![frame](data:image/jpeg;base64,{frame['base64_image']})\n"
                question += "Describe this frame in 1-2 sentences.\n\n"

            # Invoke the chain
            descriptions = self.frame_info_chain.invoke({"input": question})
            
            return descriptions

        except Exception as e:
            logger.error(f"Error analyzing frames batch: {e}")
            # Fallback to placeholder descriptions
            
        return ""

    # async def process_and_load_video(self, video_path: str) -> Dict[str, Any]:
    #     """Process a video and load it for querying"""
    #     try:
    #         self.processing_status = "processing"
    #         self.video_metadata["video_path"] = video_path

    #         # Process the video (this might be CPU-intensive)
    #         transcript_segments, frames_data, summary = await asyncio.to_thread(
    #             process_video,
    #             video_path,
    #             use_gpt4v=True,
    #             batch_size=3
    #         )

    #         # Save results
    #         await asyncio.to_thread(
    #             save_results,
    #             transcript_segments,
    #             frames_data,
    #             summary
    #         )

    #         # Initialize search
    #         await asyncio.to_thread(
    #             initialize_video_search,
    #             transcript_segments,
    #             frames_data
    #         )

    #         # Update state
    #         self.video_loaded = True
    #         self.video_metadata.update({
    #             "video_path": video_path,
    #             "duration": transcript_segments[-1]['end'] if transcript_segments else 0,
    #             "transcript_segments": len(transcript_segments),
    #             "visual_frames": len(frames_data),
    #             "summary": summary[:200] + "..." if len(summary) > 200 else summary
    #         })
    #         self.processing_status = "complete"

    #         return {
    #             "success": True,
    #             "message": f"Video '{os.path.basename(video_path)}' processed and loaded successfully",
    #             "metadata": self.video_metadata.copy()
    #         }

    #     except Exception as e:
    #         self.processing_status = "error"
    #         return {
    #             "success": False,
    #             "error": str(e)
    #         }

    async def query_video(self, question: str) -> Dict[str, Any]:
        """Query the loaded video with a natural language question"""
        if not self.video_loaded:
            return {
                "success": False,
                "error": "No video loaded. Please load a video first using /load-video endpoint."
            }

        try:
            # Use the agent to answer the question
            response = self.agent.invoke(input={"input": question})

            return {
                "success": True,
                "question": question,
                "answer": response["output"],
                "metadata": {
                    "video": self.video_metadata.get("video_path", "unknown"),
                    "timestamp": "current"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_video_summary(self) -> Dict[str, Any]:
        """Get the summary of the loaded video"""
        if not self.video_loaded:
            return {
                "success": False,
                "error": "No video loaded."
            }

        try:
            summary = await asyncio.to_thread(
                get_video_summary_tool  # type: ignore
            )

            return {
                "success": True,
                "summary": summary,
                "metadata": self.video_metadata.copy()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def search_video_content(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for specific content in the video"""
        if not self.video_loaded:
            return {
                "success": False,
                "error": "No video loaded."
            }

        try:
            results = await asyncio.to_thread(
                search_video_content_tool,
                query
            )

            return {
                "success": True,
                "query": query,
                "results": results,
                "limit": limit,
                "metadata": self.video_metadata.copy()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_video_status(self) -> Dict[str, Any]:
        """Get the current status of the video processing/loading"""
        return {
            "is_loaded": self.video_loaded,
            "processing_status": self.processing_status,
            "metadata": self.video_metadata.copy()
        }
