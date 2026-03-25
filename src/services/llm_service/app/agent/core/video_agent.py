from typing import List

from langchain.agents import create_agent
from langchain_community.vectorstores import VectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool 

from src.shared.storage.base import VectorStore
from src.shared.config.settings import settings, LLMModels
from src.shared.logging.logger import get_logger

from ..prompts import (
    agent_prompt,
    video_desc_extract_prompt_template,
    video_summary_prompt_template,
    chat_prompt
)
from ..tools import VideoSearchTool

logger = get_logger(__name__)

class VideoAnalyticsAgent:
    search_tool_instance: VideoSearchTool
    def __init__(self, model: LLMModels = settings.LLM_MODEL):
        self._init_llm(model)
        self.str_parser = StrOutputParser()
        
        # Chains (Simplified using LCEL)
        self.chains = {
            "frame": video_desc_extract_prompt_template | self.llm | self.str_parser,
            "summary": video_summary_prompt_template | self.llm | self.str_parser,
            "chat": chat_prompt | self.llm | self.str_parser
        }
        self.video_metadata = {"status": "idle"}

    def _init_llm(self, model):
        if model == LLMModels.GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.llm = ChatGoogleGenerativeAI(model=model, google_api_key=settings.GEMINI_API_KEY)
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _get_tools(self):
        """Define tools dynamically to bind to the current search instance."""
        @tool
        def search_video(query: str):
            """Search transcript and visual logs for specific content."""
            return self.search_tool_instance.search(query)

        @tool
        def temporal_analysis(events: List[str]):
            """Find chronological order of events."""
            # Reuse the search logic instead of rewriting it
            results = [self.search_tool_instance.search(e, k=1) for e in events]
            return "\n".join(results)

        return [search_video, temporal_analysis]

    def load_video(self, vector_store: VectorStore):
        """Unified processing flow."""
        self.video_metadata["status"] = "processing"
        
        # Initialize the search tool
        self.search_tool_instance = VideoSearchTool(vector_store)
        
        # Re-initialize agent with bound tools
        self.agent_executor = create_agent(
            model=self.llm, 
            tools=self._get_tools(), 
            system_prompt=agent_prompt
        )

    async def query_video(self, question: str):
        if not self.agent_executor:
            return {"error": "Video not loaded."}
    
        # Explicitly define the state dictionary
        input_data = {"input": question}
        
        try:
            # Use ainvoke with the expected dictionary structure
            res = await self.agent_executor.ainvoke(input_data) # type: ignore 
            answer = res.get("output") or res.get("agent_outcome")
            return {"answer": answer}
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {"error": str(e)}
        
    async def chat(self, question: str, chat_history: List[dict]):
        """Chat interface that maintains context."""
        if not self.agent_executor:
            return {"error": "Video not loaded."}
        
        # Prepare input with chat history
        input_data = {
            "input": question,
            "chat_history": chat_history
        }
        
        try:
            res = await self.agent_executor.ainvoke(input_data) # type: ignore 
            answer = res.get("output") or res.get("agent_outcome")
            return {"answer": answer}
        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            return {"error": str(e)}

