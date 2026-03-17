from langchain.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Optional
import os

class VideoSearchTool:
    """Handles video content indexing and search"""
    
    def __init__(self, transcript_segments: List[Dict], frames_data: List[Dict]):
        """
        Initialize with video data
        
        Args:
            transcript_segments: List of transcript segments with start/end times and text
            frames_data: List of visual frame descriptions with timestamps
        """
        self.transcript_segments = transcript_segments
        self.frames_data = frames_data
        self.vector_store = self._create_vector_store()
        # Initialize embeddings
        # env_key = os.environ.get("OPENAI_API_KEY")
        self.embeddings = OpenAIEmbeddings()
    
    def _create_vector_store(self):
        """Create vector store from video content"""
        
        # Create documents from transcript segments
        transcript_docs = []
        for seg in self.transcript_segments:
            content = f"Audio Transcript at {seg['start']:.1f}s: {seg['text']}"
            metadata = {
                "type": "transcript",
                "start_time": seg['start'],
                "end_time": seg['end'],
                "source": "audio"
            }
            transcript_docs.append(Document(page_content=content, metadata=metadata))
        
        # Create documents from visual frames
        visual_docs = []
        for frame in self.frames_data:
            content = f"Visual Scene at {frame['timestamp']:.1f}s: {frame['description']}"
            metadata = {
                "type": "visual",
                "timestamp": frame['timestamp'],
                "source": "video"
            }
            visual_docs.append(Document(page_content=content, metadata=metadata))
        
        # Combine all documents
        all_docs = transcript_docs + visual_docs
        
        # Create text chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        splits = text_splitter.split_documents(all_docs)
        
        # Create vector store (using FAISS for simplicity)
        vector_store = FAISS.from_documents(splits,self.embeddings)
        
        return vector_store
    
    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Search video content by semantic similarity"""
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                # Extract timestamp from metadata
                if doc.metadata["type"] == "transcript":
                    timestamp = doc.metadata["start_time"]
                    time_info = f"{timestamp:.1f}s - {doc.metadata['end_time']:.1f}s"
                else:
                    timestamp = doc.metadata["timestamp"]
                    time_info = f"{timestamp:.1f}s"
                
                formatted_results.append({
                    "content": doc.page_content,
                    "timestamp": timestamp,
                    "type": doc.metadata["type"],
                    "source": doc.metadata["source"],
                    "time_info": time_info,
                    "relevance_score": float(score)
                })
            
            # Sort by timestamp for chronological order
            formatted_results.sort(key=lambda x: x["timestamp"])
            return formatted_results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []

# Global state - consider using a class or singleton pattern for production
video_search_tool_instance: Optional[VideoSearchTool] = None
current_video_path: Optional[str] = None

def initialize_video_search(transcript_segments: List[Dict], frames_data: List[Dict], video_path: str = None):
    """Initialize the video search tool with processed data"""
    global video_search_tool_instance, current_video_path
    
    video_search_tool_instance = VideoSearchTool(transcript_segments, frames_data)
    if video_path:
        current_video_path = video_path
    
    print(f"Video search initialized with {len(transcript_segments)} transcript segments and {len(frames_data)} visual frames")

@tool
def search_video_content(query: str) -> str:
    """Searches the video transcript and visual logs for specific actions, objects, or dialogue.
    
    Args:
        query: Natural language query about video content (e.g., "when did the car appear", 
               "what did the driver say about the weather", "find scenes with red objects")
    
    Returns:
        Formatted string with search results including timestamps and context
    """
    if video_search_tool_instance is None:
        return "Video content not loaded. Please process a video first."
    
    results = video_search_tool_instance.search(query, k=5)
    
    if not results:
        return "No relevant content found for your query."
    
    # Format the results
    response = "Search Results:\n"
    response += "-" * 50 + "\n"
    
    for i, result in enumerate(results, 1):
        response += f"{i}. [{result['type'].upper()}] at {result['time_info']}:\n"
        response += f"   Content: {result['content']}\n"
        response += f"   Relevance: {result['relevance_score']:.3f}\n"
        response += "-" * 30 + "\n"
    
    return response

@tool
def get_video_summary() -> str:
    """Get an overall summary of the video content."""
    # Try to load saved summary - use the current video path if available
    summary_paths = [
        "output/summary.txt",
        f"output/{os.path.basename(current_video_path)}_summary.txt" if current_video_path else None,
        "summary.txt"
    ]
    
    for path in summary_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return f.read()
            except:
                continue
    
    return "Summary not available. Please process a video first."

@tool
def find_temporal_sequence(events: List[str]) -> str:
    """Find the chronological order of specific events in the video.
    
    Args:
        events: List of events to find (e.g., ["car enters", "driver speaks", "rain starts"])
    
    Returns:
        Timeline of when each event occurred
    """
    if video_search_tool_instance is None:
        return "Video content not loaded."
    
    all_results = []
    for event in events:
        results = video_search_tool_instance.search(event, k=2)
        if results:
            all_results.extend(results)
    
    if not all_results:
        return "No matching events found."
    
    # Sort by timestamp
    all_results.sort(key=lambda x: x["timestamp"])
    
    response = "Chronological Sequence of Events:\n"
    response += "=" * 50 + "\n"
    
    for i, result in enumerate(all_results, 1):
        response += f"{i}. {result['time_info']} ({result['type']}):\n"
        response += f"   {result['content'][:100]}...\n"
    
    return response

@tool
def analyze_visual_patterns(pattern_type: str) -> str:
    """Analyze specific visual patterns in the video.
    
    Args:
        pattern_type: Type of pattern to analyze 
                     (e.g., "color_changes", "object_movements", "scene_transitions")
    
    Returns:
        Analysis of the visual patterns
    """
    if video_search_tool_instance is None:
        return "Video content not loaded."
    
    # Search for relevant visual frames
    pattern_keywords = {
        "color_changes": ["red", "blue", "green", "color", "changes", "bright", "dark"],
        "object_movements": ["moves", "enters", "exits", "approaches", "leaves", "travels"],
        "scene_transitions": ["cut to", "transition", "new scene", "changes to", "different"]
    }
    
    keywords = pattern_keywords.get(pattern_type, [pattern_type])
    query = " OR ".join(keywords)
    
    results = video_search_tool_instance.search(query, k=10)
    visual_results = [r for r in results if r["type"] == "visual"]
    
    if not visual_results:
        return f"No {pattern_type} patterns found."
    
    response = f"Analysis of {pattern_type}:\n"
    response += "=" * 50 + "\n"
    
    for result in visual_results:
        response += f"• At {result['time_info']}:\n"
        response += f"  {result['content'][:80]}...\n"
    
    response += f"\nTotal {pattern_type} instances: {len(visual_results)}"
    return response

# Additional helper functions

def get_video_search_instance() -> Optional[VideoSearchTool]:
    """Get the current video search instance"""
    return video_search_tool_instance

def clear_video_search():
    """Clear the current video search instance"""
    global video_search_tool_instance, current_video_path
    video_search_tool_instance = None
    current_video_path = None
    print("Video search cleared")