"""
Local filesystem storage provider
"""
import aiofiles
from typing import BinaryIO, Optional
from fastapi import UploadFile
from pathlib import Path
from .base_storage import StorageProvider
from src.shared.logging.logger import get_logger
from src.shared.config.settings import settings
from langchain_chroma import Chroma
from langchain_community.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = get_logger(__name__)

class LocalStorageProvider(StorageProvider):
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.videos_path = self.base_path / "videos"
        self.transcripts_path = self.base_path / "transcripts"
        self.summaries_path = self.base_path / "summaries"
        self.cache_path = self.base_path / "cache"
        self.meta_data_path = self.base_path / "metadata"
        
        for path in [self.videos_path, self.transcripts_path, 
                    self.summaries_path, self.cache_path, self.meta_data_path]:
            path.mkdir(parents=True, exist_ok=True)

    def _get_chunks(self,docs):
        # Split the transcript into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.create_documents([docs])

        print(f"Total chunks created: {len(chunks)}")
        return chunks

    def _create_vector_store(self,docs, embeddings, PERSIST_DIR="data/vectors", COLLECTION_NAME="default_collection"):
        # Create and persist Chroma vector store
        vectordb = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=PERSIST_DIR,
            collection_name=COLLECTION_NAME
        )
        
        print(f"Vector database stored successfully in {PERSIST_DIR}")

    def _load_vector_store(self,embedding_model,persist_directory: str = "data/vectors", collection_name: str = "default_collection",) -> VectorStore:
        vectordb = Chroma(embedding_function=embedding_model,persist_directory=persist_directory, collection_name=collection_name)
        return vectordb

    
    def _get_full_path(self, file_path: str) -> Path:
        """Convert relative path to absolute path"""
        return self.base_path / file_path
    
    async def save_file(self, file: BinaryIO, file_path: str) -> str:
        """Save a file to local storage"""
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiofiles.open(full_path, 'wb') as f:
                # Read file in chunks to handle large files
                chunk_size = 1024 * 1024  # 1MB chunks
                while chunk := file.read(chunk_size):
                    await f.write(chunk)
            
            logger.info(f"File saved: {full_path}")
            return str(full_path)
            
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {str(e)}")
            raise
    
    async def get_file(self, file_path: str) -> Optional[BinaryIO]:
        """Retrieve a file from local storage"""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        try:
            return open(full_path, 'rb')
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from local storage"""
        full_path = self._get_full_path(file_path)
        
        try:
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        full_path = self._get_full_path(file_path)
        return full_path.exists()
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get file URL (for local storage, returns file path)"""
        full_path = self._get_full_path(file_path)
        if full_path.exists():
            return f"file://{full_path}"
        return None
    
    async def list_files(self, prefix: str = "") -> list:
        """List files in storage"""
        search_path = self._get_full_path(prefix)
        
        print(f"Listing files in: {search_path}")

        if not search_path.exists():
            return []
        
        files = []
        for item in search_path.rglob("*"):
            if item.is_file():
                rel_path = str(item.relative_to(self.base_path))
                files.append({
                    "name": item.name,
                    "path": rel_path,
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime
                })
        
        return files
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        full_path = self._get_full_path(file_path)
        
        if full_path.exists():
            return full_path.stat().st_size
        return 0
    
  