
import json
from typing import List, Optional, BinaryIO, Dict, Any
from io import BytesIO
from os import path
from fastapi import UploadFile
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.services.video_processing.app.contracts.schemas import VideoProcessingStatus
from src.shared.config.settings import settings
from src.shared.storage.base.base_cache import CacheProvider
from src.shared.storage.base.base_vector_store import VectorStore, VectorStoreProvider
from src.shared.contracts.video_metadata import VideoMetadata
from src.shared.storage.base.base_storage import StorageProvider
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)


class VideoRepository:
    def __init__(self, storage: StorageProvider, vector_store: VectorStoreProvider, cache: CacheProvider):
        self.storage = storage
        self.vector_store = vector_store
        self.cache = cache

    async def save_video_metadata(self, metadata: VideoMetadata) -> str:
        """Save video metadata"""
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_filename = f"metadata/{metadata.id}{ext}"

        # mode='json' converts datetimes to strings automatically
        metadata_dict = metadata.model_dump(mode='json')

        # Now json.dumps will work because there are no more datetime objects
        content = BytesIO(json.dumps(metadata_dict, indent=2).encode('utf-8'))

        await self.storage.save_file(content, metadata_filename)

        await self.set_video_metadata(metadata.id, metadata)

        return metadata_filename

    async def save_raw_video(self, video_id: str, file_stream: BinaryIO):
        """Handles the actual file persistence"""
        path = f"videos/{video_id}.mp4"
        return await self.storage.save_file(file_stream, path)

    async def get_video_status(self, video_id: str) -> Optional[VideoProcessingStatus]:
        """Get processing status of a video"""
        data: Optional[str] = await self.cache.get(f"video:{video_id}:status")
        if not data:
            return None
        try:
            status = VideoProcessingStatus.model_validate_json(data)
            logger.info(
                f"Get Video Status for {video_id}: {status.current_stage}, {status.progress*100:.2f}%")
            return status
        except Exception as e:
            # If the data in Redis is corrupt or double-encoded
            logger.error(f"Failed to parse status for {video_id}: {e}")
            return None

    async def set_video_status(self, video_id: str, status: VideoProcessingStatus):
        """Set processing status of a video"""
        await self.cache.set(
            key=f"video:{video_id}:status",
            value=status.model_dump_json()
        )

    async def set_video_results(self, video_id: str, results: Dict[str, Any]):
        """Set processing results and increment global count atomically"""
        await self.cache.set(
            key=f"video:{video_id}:results",
            value=json.dumps(results),
            ttl=86400  # Extend to 24 hours so users don't lose results immediately
        )
        # This is now thread-safe!
        await self.cache.increment(f"video:results:count")

    async def get_processed_count(self) -> int:
        """Get processed count of a video"""
        data = await self.cache.get(f"video:results:count")
        if data:
            count = json.loads(data)
            return count
        return 0

    async def set_processed_count(self, count: int):
        """Set processed count of a video"""
        await self.cache.set(
            key=f"video:results:count",
            value=json.dumps(count)
        )
        return 0

    async def remove_video_status(self, video_id: str):
        """Remove processing status of a video"""
        await self.cache.delete(f"video:{video_id}:status")

    async def set_video_metadata(self, video_id: str, metadata: VideoMetadata):
        """Set video metadata"""
        await self.cache.set(
            key=f"video:{video_id}:metadata",
            value=metadata.model_dump_json()
        )

    async def remove_video_metadata(self, video_id: str):
        """Remove video metadata"""
        await self.cache.delete(
            key=f"video:{video_id}:metadata"
        )

    # Video-specific operations

    async def save_video(self, file: UploadFile, video_id: str) -> str:
        """Save video file with standardized naming"""
        # Get file extension
        filename = file.filename or f"video_{video_id}"
        ext = '.' + filename.split('.')[-1] if '.' in filename else '.mp4'
        video_path = f"videos/{video_id}{ext}"

        # Pass the file object directly to the provider - it can handle streaming or in-memory as needed
        return await self.storage.save_file(file.file, video_path)

    async def _get_metadata_from_storage(self, video_id: str) -> Optional[VideoMetadata]:
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_filename = f"metadata/{video_id}{ext}"

        # 1. Check existence first
        if not await self.storage.file_exists(metadata_filename):
            return None

        file_obj = await self.storage.get_file(metadata_filename)
        if not file_obj:
            return None

        try:
            # 2. Handle the read - if file_obj is a stream,
            # some providers require 'await file_obj.read()'
            content = file_obj.read()
            if hasattr(content, '__await__'):  # Defensive check for async streams
                content = await content

            data = json.loads(content.decode('utf-8'))

            # 3. Pydantic will automatically convert the JSON strings
            # back into datetime objects here.
            return VideoMetadata(**data)

        except Exception as e:
            logger.error(f"Error loading metadata for {video_id}: {str(e)}")
            return None
        finally:
            # 4. Ensure cleanup
            if file_obj and hasattr(file_obj, 'close'):
                file_obj.close()

    async def _get_metadata_from_cache(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata from cache"""
        data: Optional[str] = await self.cache.get(f"video:{video_id}:metadata")
        if not data:
            return None
        return VideoMetadata.model_validate_json(data)

    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata"""

        # 1. Try Cache first
        cached_data = await self._get_metadata_from_cache(video_id)

        if cached_data:
            return cached_data

        # 2. Fallback to Storage (Disk/S3)
        metadata = await self._get_metadata_from_storage(video_id)

        # 3. Populate Cache for next time
        if metadata:
            await self.cache.set(f"video:{video_id}:metadata", metadata.model_dump_json())

        return metadata

    async def save_transcript(self, video_id: str, transcript_data: Dict[str, Any]) -> str:
        """Save transcript data"""
        transcript_path = f"transcripts/{video_id}.json"
        content = BytesIO(json.dumps(
            transcript_data, indent=2).encode('utf-8'))
        return await self.storage.save_file(content, transcript_path)

    async def get_transcript(self, video_id: str, format: str = "json") -> Optional[Any]:
        """Get transcript for a video"""
        transcript_path = f"transcripts/{video_id}.{format}"

        if not await self.storage.file_exists(transcript_path):
            return None

        file_obj = await self.storage.get_file(transcript_path)
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
        return await self.storage.save_file(content, summary_path)

    async def list_videos(self, page, limit, status) -> List[VideoMetadata]:
        """List all videos in storage"""
        metadatas = await self.storage.list_files("metadata/")

        logger.debug(f"Found {len(metadatas)} metadata files in storage")

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

        if not await self.storage.file_exists(summary_path):
            return None

        file_obj = await self.storage.get_file(summary_path)
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
        return await self.storage.save_file(content, frames_path)

    async def get_frames_data(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get frames data for a video"""
        frames_path = f"frames/{video_id}.json"

        if not await self.storage.file_exists(frames_path):
            return None

        file_obj = await self.storage.get_file(frames_path)
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
        videos = await self.storage.list_files("videos/")
        for video in videos:
            if video_id in video.get('name', '') or video_id in video.get('path', ''):
                success = success and await self.storage.delete_file(video['path'])

        # Delete transcript files
        for format in ["json", "txt", "srt"]:
            transcript_path = f"transcripts/{video_id}.{format}"
            if await self.storage.file_exists(transcript_path):
                success = success and await self.storage.delete_file(transcript_path)

        # Delete summary
        summary_path = f"summaries/{video_id}.txt"
        if await self.storage.file_exists(summary_path):
            success = success and await self.storage.delete_file(summary_path)

        # Delete frames
        frames_path = f"frames/{video_id}.json"
        if await self.storage.file_exists(frames_path):
            success = success and await self.storage.delete_file(frames_path)

        # Delete metadata
        ext = settings.STORAGE_VIDEO_METADATA_EXT
        metadata_path = f"metadata/{video_id}{ext}"
        if await self.storage.file_exists(metadata_path):
            success = success and await self.storage.delete_file(metadata_path)

        # Delete cached data
        cache_files = await self.storage.list_files(f"cache/{video_id}")
        for cache_file in cache_files:
            success = success and await self.storage.delete_file(cache_file['path'])

        # Delete any other related files (e.g. thumbnails)
        thumbnails = await self.storage.list_files("thumbnails/")
        for thumbnail in thumbnails:
            if video_id in thumbnail.get('name', '') or video_id in thumbnail.get('path', ''):
                success = success and await self.storage.delete_file(thumbnail['path'])
        return success

    async def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics"""
        files = await self.storage.list_files()
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
            'provider': type(self.storage).__name__,
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

    async def save_embeddings(self, video_id: str, embeddings: List[Dict[str, Any]]) -> bool:
        """Save vector embeddings for a video"""
        try:
            await self.vector_store.upsert_vectors(video_id, embeddings)
            return True
        except Exception as e:
            logger.error(f"Error saving embeddings for {video_id}: {str(e)}")
            return False


    async def clear_storage(self) -> bool:
        """Clear all files from storage - USE WITH CAUTION"""
        files = await self.storage.list_files()
        success = True
        for file_info in files:
            success = success and await self.storage.delete_file(file_info['path'])
        return success
    
    async def get_vector_store(self, video_id: str) -> VectorStore:
        """Get the standardized path for the vector store index file"""
        return await self.vector_store.get_vector_store(video_id)
    
    async def vector_store_exists(self, video_id: str) -> bool:
        """Check if vector store index file exists in storage"""
        return await self.vector_store.vector_store_exists(video_id)

    async def _get_or_create_vector_store(self, video_id: str):   
        # Check if vector store already exists
        if await self.vector_store.vector_store_exists(video_id):
            return True
        
        # Create new vector store
        # Load transcript and frames data
        transcript_segments = await self.get_transcript(video_id)
        frames_data = await self.get_frames_data(video_id)

        if transcript_segments is None or frames_data is None:
            logger.error(f"Cannot create vector store for {video_id}: Missing transcript or frames data")
            return False


        docs = []
        # Combine creation logic to avoid code duplication
        for seg in transcript_segments:
            docs.append(Document(
            page_content=f"Audio Transcript [{seg['start']:.1f}s]: {seg['text']}",
            metadata={"type": "transcript", "start": seg['start'], "end": seg['end']}
        ))
        for frame in frames_data:
            docs.append(Document(
                page_content=f"Visual Scene [{frame['timestamp']:.1f}s]: {frame['description']}",
                metadata={"type": "visual", "timestamp": frame['timestamp']}
            ))
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        return FAISS.from_documents(text_splitter.split_documents(docs), self.embeddings)

