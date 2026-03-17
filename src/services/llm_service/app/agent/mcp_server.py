import uvicorn
from mcp.server.fastmcp import FastMCP
import nest_asyncio
import json
from typing import Dict, Any

# Import from local modules
from src.agent.core.video_agent import VideoAnalyticsAgent


class VideoAnalyticsServerProvider:
    """MCP Server for Video Analytics Agent"""
    
    def __init__(self):
        self._agent = VideoAnalyticsAgent()
        self._mcp = FastMCP(
            name="VideoAnalyticsAgent",
            instructions="A powerful video analysis agent that can process videos and answer questions about their content.",
        )
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self._mcp.tool()
        async def load_video(video_path: str) -> str:
            """
            Load and process a video file for analysis.
            
            Args:
                video_path: Path to the video file to analyze
            """
            result = await self._agent.process_and_load_video(video_path)
            return json.dumps(result, indent=2)
        
        @self._mcp.tool()
        async def query_video(question: str) -> str:
            """
            Ask a question about the currently loaded video.
            
            Args:
                question: Natural language question about the video content
            """
            result = await self._agent.query_video(question)
            return json.dumps(result, indent=2)
        
        @self._mcp.tool()
        async def video_summary() -> str:
            """Get a comprehensive summary of the loaded video."""
            result = await self._agent.get_video_summary()
            return json.dumps(result, indent=2)
        
        @self._mcp.tool()
        async def search_video(query: str, limit: int = 5) -> str:
            """
            Search for specific content in the video.
            
            Args:
                query: Search query
                limit: Maximum number of results (default: 5)
            """
            result = await self._agent.search_video_content(query, limit)
            return json.dumps(result, indent=2)
        
        @self._mcp.tool()
        async def video_status() -> str:
            """Get the current status of video processing/loading."""
            result = await self._agent.get_video_status()
            return json.dumps(result, indent=2)
        
        @self._mcp.tool()
        async def example_queries() -> str:
            """Get example questions you can ask about videos."""
            examples = {
                "content_analysis": [
                    "What are the main topics discussed in the video?",
                    "Summarize the key points from the first 5 minutes",
                    "What arguments or opinions are presented?",
                ],
                "visual_analysis": [
                    "Describe the key visual elements and when they appear",
                    "Are there any notable color changes or visual patterns?",
                    "What objects or people are most prominent visually?",
                ],
                "temporal_analysis": [
                    "What happens between 2:00 and 5:00 minutes?",
                    "When does the main event occur and what leads up to it?",
                    "Show me the chronological sequence of important events",
                ],
                "specific_queries": [
                    "Find all mentions of [specific topic or keyword]",
                    "When does [specific person or object] appear?",
                    "What was said about [specific subject]?",
                ],
                "pattern_analysis": [
                    "What visual patterns show movement in the video?",
                    "Are there recurring themes or motifs?",
                    "How does the lighting or mood change over time?",
                ]
            }
            
            return json.dumps({"examples": examples}, indent=2)
        
        @self._mcp.tool()
        async def analyze_specific_timeframe(start_time: float, end_time: float) -> str:
            """
            Analyze a specific timeframe within the video.
            
            Args:
                start_time: Start time in seconds
                end_time: End time in seconds
            """
            status = await self._agent.get_video_status()
            if not status["is_loaded"]:
                return json.dumps({
                    "success": False,
                    "error": "No video loaded."
                }, indent=2)
            
            try:
                question = f"What happens between {start_time} and {end_time} seconds in the video?"
                result = await self._agent.query_video(question)
                
                # Add timeframe metadata
                if result["success"]:
                    result["timeframe"] = {
                        "start": start_time,
                        "end": end_time,
                        "duration": end_time - start_time
                    }
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
        
        @self._mcp.tool()
        async def compare_timeframes(timeframe1: Dict[str, float], timeframe2: Dict[str, float]) -> str:
            """
            Compare two different timeframes in the video.
            
            Args:
                timeframe1: {"start": float, "end": float}
                timeframe2: {"start": float, "end": float}
            """
            status = await self._agent.get_video_status()
            if not status["is_loaded"]:
                return json.dumps({
                    "success": False,
                    "error": "No video loaded."
                }, indent=2)
            
            try:
                # Analyze both timeframes
                question1 = f"Describe what happens between {timeframe1['start']} and {timeframe1['end']} seconds"
                question2 = f"Describe what happens between {timeframe2['start']} and {timeframe2['end']} seconds"
                
                result1 = await self._agent.query_video(question1)
                result2 = await self._agent.query_video(question2)
                
                # Create a comparison question
                comparison_question = f"""
                Compare these two timeframes from the video:
                
                Timeframe 1 ({timeframe1['start']}-{timeframe1['end']}s): {result1['answer'][:100] if result1['success'] else 'Analysis failed'}...
                
                Timeframe 2 ({timeframe2['start']}-{timeframe2['end']}s): {result2['answer'][:100] if result2['success'] else 'Analysis failed'}...
                
                What are the similarities and differences? What changes occur between them?
                """
                
                comparison_result = await self._agent.query_video(comparison_question)
                
                return json.dumps({
                    "success": True,
                    "comparison": comparison_result['answer'] if comparison_result['success'] else "Comparison failed",
                    "timeframes": {
                        "timeframe1": {
                            **timeframe1,
                            "analysis": result1['answer'] if result1['success'] else "Analysis failed"
                        },
                        "timeframe2": {
                            **timeframe2,
                            "analysis": result2['answer'] if result2['success'] else "Analysis failed"
                        }
                    }
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                }, indent=2)
    
    def run(self):
        """Run the MCP server"""
        print("Starting Video Analytics Agent MCP Server...")
        print("=" * 60)
        print("Available tools:")
        print("  • load_video(video_path) - Load and process a video")
        print("  • query_video(question) - Ask questions about the video")
        print("  • video_summary() - Get comprehensive video summary")
        print("  • search_video(query, limit=5) - Search video content")
        print("  • video_status() - Check video processing status")
        print("  • example_queries() - Get example questions")
        print("  • analyze_specific_timeframe(start_time, end_time)")
        print("  • compare_timeframes(timeframe1, timeframe2)")
        print("=" * 60)
        
        nest_asyncio.apply()
        self._mcp.run()
    
    def run_http_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the HTTP server"""
        print(f"Starting HTTP server on http://{host}:{port}")
        uvicorn.run(self._mcp, host=host, port=port)


if __name__ == "__main__":
    provider = VideoAnalyticsServerProvider()
    http = False
    
    if http:
        provider.run_http_server()
    else:
        provider.run()