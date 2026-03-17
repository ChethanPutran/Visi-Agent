"""
S3-compatible storage provider (AWS S3, MinIO, etc.)
"""
# import boto3
# from botocore.exceptions import ClientError
from typing import BinaryIO, Optional
from fastapi import UploadFile
import io
from .base_storage import StorageProvider
from src.shared.config.settings import settings
from src.shared.logging.logger import get_logger

logger = get_logger(__name__)

class CloudStorageProvider(StorageProvider):
    def __init__(self):
       pass
    
    
    async def save_file(self, file: UploadFile, file_path: str) -> str:
        return ""


# class S3StorageProvider(StorageProvider):
#     def __init__(self):
#         self.bucket_name = settings.S3_BUCKET
#         self.endpoint_url = settings.S3_ENDPOINT
        
#         self.s3_client = boto3.client(
#             's3',
#             endpoint_url=self.endpoint_url,
#             aws_access_key_id=settings.S3_ACCESS_KEY,
#             aws_secret_access_key=settings.S3_SECRET_KEY,
#             region_name=settings.S3_REGION
#         )
        
#         # Ensure bucket exists
#         self._ensure_bucket()
    
#     def _ensure_bucket(self):
#         """Create bucket if it doesn't exist"""
#         try:
#             self.s3_client.head_bucket(Bucket=self.bucket_name)
#         except ClientError:
#             try:
#                 self.s3_client.create_bucket(Bucket=self.bucket_name)
#                 logger.info(f"Created bucket: {self.bucket_name}")
#             except Exception as e:
#                 logger.error(f"Failed to create bucket: {str(e)}")
#                 raise
    
#     async def save_file(self, file: UploadFile, file_path: str) -> str:
#         """Upload file to S3"""
#         try:
#             # Read file content
#             content = await file.read()
            
#             # Upload to S3
#             self.s3_client.put_object(
#                 Bucket=self.bucket_name,
#                 Key=file_path,
#                 Body=content,
#                 ContentType=file.content_type,
#                 Metadata={
#                     'original-filename': file.filename,
#                     'size': str(file.size)
#                 }
#             )
            
#             logger.info(f"File uploaded to S3: {file_path}")
#             return file_path
            
#         except Exception as e:
#             logger.error(f"Failed to upload to S3: {str(e)}")
#             raise
    
#     async def get_file(self, file_path: str) -> Optional[BinaryIO]:
#         """Download file from S3"""
#         try:
#             response = self.s3_client.get_object(
#                 Bucket=self.bucket_name,
#                 Key=file_path
#             )
#             return io.BytesIO(response['Body'].read())
#         except ClientError as e:
#             if e.response['Error']['Code'] == 'NoSuchKey':
#                 logger.warning(f"File not found in S3: {file_path}")
#                 return None
#             logger.error(f"Failed to download from S3: {str(e)}")
#             raise
    
#     async def delete_file(self, file_path: str) -> bool:
#         """Delete file from S3"""
#         try:
#             self.s3_client.delete_object(
#                 Bucket=self.bucket_name,
#                 Key=file_path
#             )
#             logger.info(f"File deleted from S3: {file_path}")
#             return True
#         except ClientError as e:
#             logger.error(f"Failed to delete from S3: {str(e)}")
#             return False
    
#     async def file_exists(self, file_path: str) -> bool:
#         """Check if file exists in S3"""
#         try:
#             self.s3_client.head_object(
#                 Bucket=self.bucket_name,
#                 Key=file_path
#             )
#             return True
#         except ClientError as e:
#             if e.response['Error']['Code'] == '404':
#                 return False
#             raise
    
#     async def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
#         """Generate pre-signed URL for file"""
#         try:
#             url = self.s3_client.generate_presigned_url(
#                 'get_object',
#                 Params={
#                     'Bucket': self.bucket_name,
#                     'Key': file_path
#                 },
#                 ExpiresIn=expires_in
#             )
#             return url
#         except Exception as e:
#             logger.error(f"Failed to generate pre-signed URL: {str(e)}")
#             return None
    
#     async def list_files(self, prefix: str = "") -> list:
#         """List files in S3 bucket"""
#         try:
#             response = self.s3_client.list_objects_v2(
#                 Bucket=self.bucket_name,
#                 Prefix=prefix
#             )
            
#             files = []
#             for obj in response.get('Contents', []):
#                 files.append({
#                     'name': obj['Key'].split('/')[-1],
#                     'path': obj['Key'],
#                     'size': obj['Size'],
#                     'modified': obj['LastModified'].timestamp()
#                 })
            
#             return files
#         except Exception as e:
#             logger.error(f"Failed to list S3 files: {str(e)}")
#             return []
    
#     async def get_file_size(self, file_path: str) -> int:
#         """Get file size from S3"""
#         try:
#             response = self.s3_client.head_object(
#                 Bucket=self.bucket_name,
#                 Key=file_path
#             )
#             return response['ContentLength']
#         except ClientError:
#             return 0
    
#     async def save_video(self, file: UploadFile, video_id: str) -> str:
#         """Save video to videos/ directory in S3"""
#         ext = '.' + file.filename.split('.')[-1] if '.' in file.filename else '.mp4'
#         video_key = f"videos/{video_id}{ext}"
#         return await self.save_file(file, video_key)