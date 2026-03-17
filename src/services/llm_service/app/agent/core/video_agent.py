import asyncio
import os
from typing import Dict, Any, List
from langchain.agents import create_agent
from langchain.messages import SystemMessage
from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
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

    def __init__(self, model='google'):
        """Initialize the LangChain agent with tools"""
        self.video_loaded = False
        self.video_metadata = {}
        self.processing_status = "idle"
        self.agent_executor = None
        self.llm  = None
        if model=="openai":
            # self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
            pass
        elif model=="google":
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-3-flash-preview",
                temperature=1.0,  # Gemini 3.0+ defaults to 1.0
                max_tokens=None,
                timeout=None,
                max_retries=2
            )

        # Wrap the system message in a PromptTemplate
        self.video_desc_extract_prompt_template = PromptTemplate.from_template("""You are a video analytics agent. I'll show you several video frames with their timestamps.
            For each frame, describe what you see in 1-2 sentences.
            """)
        # Wrap the system message in a PromptTemplate
        self.video_summary_prompt_template = PromptTemplate.from_template("""Based on the following video transcript and visual descriptions, create a comprehensive summary:

        TRANSCRIPT:
        {transcript_text}

        VISUAL DESCRIPTIONS (Key Frames):
        {visual_context}

        Please provide:
        1. A 3-4 sentence overview of the video
        2. Key topics discussed
        3. Main visual elements
        4. Any important actions or events

        Summary:""")

        self.str_parser = StrOutputParser()

        self.tools = [
            search_video_content_tool,
            get_video_summary_tool,
            find_temporal_sequence,
            analyze_visual_patterns
        ]

        self.agent_prompt = SystemMessage(
            "You are a video analytics agent. Use the provided tools to answer questions about the video\
            content, summary, and visual patterns."
        )
        self.frame_info_chain = self.video_desc_extract_prompt_template | self.llm | self.str_parser
        self.summary_chain = self.video_summary_prompt_template | self.llm | self.str_parser

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.agent_prompt
        )

    def generate_video_summary(self, transcript_segments: List[Dict], frames_data: List[Dict]) -> str:
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

    def analyze_frames_batch(self, frames_batch: List[Dict]) -> str:
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
