"""
Base storage interface
"""
from abc import ABC, abstractmethod
from typing import Any, BinaryIO, Optional


class StorageProvider(ABC):
    """Abstract base class for storage providers"""
    
    @abstractmethod
    async def save_file(self, file: Any, file_path: str) -> str:
        """Save a file to storage"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> Optional[Any]:
        """Retrieve a file from storage"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        pass
    
    @abstractmethod
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get a temporary URL for the file"""
        pass
    
    @abstractmethod
    async def list_files(self, prefix: str = "") -> list:
        """List files in storage"""
        pass
    
    @abstractmethod
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        pass
