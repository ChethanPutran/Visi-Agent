from importlib.resources import path
import json
from os import path
from typing import List, Optional, BinaryIO, Dict, Any
from fastapi import UploadFile
import redis
from src.shared.config.settings import settings
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.storage.base_storage import StorageProvider
from src.shared.storage.local_storage import LocalStorageProvider
from io import BytesIO
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class StorageProviders:
    LOCAL="local"
    REMOTE="remote"

class StorageService:
    """Unified storage service with provider abstraction"""
    
    _instance = None
    _provider:StorageProvider

    def __init__(self, storage_provider: str):
        if self._initialized:
            return
        
        if storage_provider == StorageProviders.LOCAL:
            self._provider = LocalStorageProvider(settings.STORAGE_PATH)

        logger.info(f"Using local storage at {settings.STORAGE_PATH}")
        self._initialized = True

    # Singleton pattern   
    def __new__(cls, storage_provider: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @property
    def provider(self) -> StorageProvider:
        """Get the current storage provider"""
        return self._provider 
    
    # File operations
    async def save_file(self, file: BinaryIO, file_path: str) -> str:
        """Save a file to storage"""
        return await self.provider.save_file(file, file_path)
    
    async def get_file(self, file_path: str) -> Optional[BinaryIO]:
        """Retrieve a file from storage"""
        return await self.provider.get_file(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        return await self.provider.delete_file(file_path)
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        return await self.provider.file_exists(file_path)
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get a temporary URL for the file"""
        return await self.provider.get_file_url(file_path, expires_in)
    
    async def list_files(self, prefix: str = "") -> list:
        """List files in storage"""
        return await self.provider.list_files(prefix)
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return await self.provider.get_file_size(file_path)
    
    # Video-specific operations
    async def save_video(self, file: UploadFile, video_id: str) -> str:
        """Save video file with standardized naming"""
        # Get file extension
        filename = file.filename or f"video_{video_id}"
        ext = '.' + filename.split('.')[-1] if '.' in filename else '.mp4'
        video_path = f"videos/{video_id}{ext}"
        
        # Convert UploadFile to BinaryIO
        file_content = await file.read()
        file_io = BytesIO(file_content)
        
        # Save file
        return await self.save_file(file_io, video_path)
    
    async def save_video_metadata(self, metadata: VideoMetadata) -> str:
        """Save video metadata"""
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_filename = f"metadata/{metadata.id}{ext}"
        
        # Convert metadata to JSON bytes
        metadata_dict = metadata.dict() if hasattr(metadata, 'dict') else vars(metadata)
        content = BytesIO(json.dumps(metadata_dict, indent=2).encode('utf-8'))
        
        return await self.provider.save_file(content, metadata_filename)
    
    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_filename = f"metadata/{video_id}{ext}"
        
        if not await self.file_exists(metadata_filename):
            return None
        
        file_obj = await self.get_file(metadata_filename)
        if not file_obj:
            return None
        
        try:
            content = file_obj.read().decode('utf-8')
            data = json.loads(content)
            return VideoMetadata(**data)
        except Exception as e:
            logger.error(f"Error loading metadata for {video_id}: {str(e)}")
            return None
        finally:
            if file_obj:
                file_obj.close()
    
    async def save_transcript(self, video_id: str, transcript_data: Dict[str, Any]) -> str:
        """Save transcript data"""
        transcript_path = f"transcripts/{video_id}.json"
        content = BytesIO(json.dumps(transcript_data, indent=2).encode('utf-8'))
        return await self.save_file(content, transcript_path)
    
    async def get_transcript(self, video_id: str, format: str = "json") -> Optional[Any]:
        """Get transcript for a video"""
        transcript_path = f"transcripts/{video_id}.{format}"
        
        if not await self.file_exists(transcript_path):
            return None
        
        file_obj = await self.get_file(transcript_path)
        if not file_obj:
            return None
        
        try:
            content = file_obj.read().decode('utf-8')
            if format == "json":
                return json.loads(content)
            return content
        except Exception as e:
            logger.error(f"Error loading transcript for {video_id}: {str(e)}")
            return None
        finally:
            if file_obj:
                file_obj.close()
    
    async def save_summary(self, video_id: str, summary: str) -> str:
        """Save video summary"""
        summary_path = f"summaries/{video_id}.txt"
        content = BytesIO(summary.encode('utf-8'))
        return await self.save_file(content, summary_path)
    
    async def list_videos(self,page, limit, status)->List[VideoMetadata]:
        """List all videos in storage"""
        metadatas = await self.list_files("metadata/")

        print(f"Found {len(metadatas)} metadata files in storage")

        videos = []
        for metadata in metadatas:
            video_id = path.basename(metadata['name']).split('.')[0]
            metadata_obj = await self.get_video_metadata(video_id)

            if metadata_obj and isinstance(metadata_obj, VideoMetadata):
                videos.append(metadata_obj)
        return videos
    
    async def get_summary(self, video_id: str) -> Optional[str]:
        """Get summary for a video"""
        summary_path = f"summaries/{video_id}.txt"
        
        if not await self.file_exists(summary_path):
            return None
        
        file_obj = await self.get_file(summary_path)
        if not file_obj:
            return None
        
        try:
            return file_obj.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error loading summary for {video_id}: {str(e)}")
            return None
        finally:
            if file_obj:
                file_obj.close()
    
    async def save_frames(self, video_id: str, frames_data: Dict[str, Any]) -> str:
        """Save frames data"""
        frames_path = f"frames/{video_id}.json"
        content = BytesIO(json.dumps(frames_data, indent=2).encode('utf-8'))
        return await self.save_file(content, frames_path)
    
    async def get_frames_data(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get frames data for a video"""
        frames_path = f"frames/{video_id}.json"
        
        if not await self.file_exists(frames_path):
            return None
        
        file_obj = await self.get_file(frames_path)
        if not file_obj:
            return None
        
        try:
            content = file_obj.read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading frames data for {video_id}: {str(e)}")
            return None
        finally:
            if file_obj:
                file_obj.close()
    
    async def delete_video_data(self, video_id: str) -> bool:
        """Delete all data associated with a video"""
        success = True
        
        # Find and delete video file
        videos = await self.list_files("videos/")
        for video in videos:
            if video_id in video.get('name', '') or video_id in video.get('path', ''):
                success = success and await self.delete_file(video['path'])
        
        # Delete transcript files
        for format in ["json", "txt", "srt"]:
            transcript_path = f"transcripts/{video_id}.{format}"
            if await self.file_exists(transcript_path):
                success = success and await self.delete_file(transcript_path)
        
        # Delete summary
        summary_path = f"summaries/{video_id}.txt"
        if await self.file_exists(summary_path):
            success = success and await self.delete_file(summary_path)
        
        # Delete frames
        frames_path = f"frames/{video_id}.json"
        if await self.file_exists(frames_path):
            success = success and await self.delete_file(frames_path)
        
        # Delete metadata
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_path = f"metadata/{video_id}{ext}"
        if await self.file_exists(metadata_path):
            success = success and await self.delete_file(metadata_path)
        
        # Delete cached data
        cache_files = await self.list_files(f"cache/{video_id}")
        for cache_file in cache_files:
            success = success and await self.delete_file(cache_file['path'])
        
        return success
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics"""
        files = await self.list_files()
        total_size = 0
        
        # Categorize files
        videos = []
        transcripts = []
        summaries = []
        frames = []
        metadata = []
        cache = []
        
        for file_info in files:
            path = file_info.get('path', '')
            size = file_info.get('size', 0)
            total_size += size
            
            if path.startswith('videos/'):
                videos.append(file_info)
            elif path.startswith('transcripts/'):
                transcripts.append(file_info)
            elif path.startswith('summaries/'):
                summaries.append(file_info)
            elif path.startswith('frames/'):
                frames.append(file_info)
            elif path.startswith('metadata/'):
                metadata.append(file_info)
            elif path.startswith('cache/'):
                cache.append(file_info)
        
        return {
            'provider': type(self.provider).__name__,
            'total_files': len(files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'by_type': {
                'videos': len(videos),
                'transcripts': len(transcripts),
                'summaries': len(summaries),
                'frames': len(frames),
                'metadata': len(metadata),
                'cache': len(cache)
            }
        }


    