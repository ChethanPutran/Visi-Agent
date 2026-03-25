from src.shared.storage.base import VectorStore


class VideoSearchTool:
    """Handles video content indexing, search, and retrieval logic."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def search(self, query: str, k: int = 5) -> str:
        """Centralized search formatting used by all tools."""
        results = self.vector_store.similarity_search(query, k=k)
        if not results: return "No relevant content found."
        
        return "\n---\n".join([f"[{d.metadata.get('type')}] {d.page_content}" for d in results])
    
