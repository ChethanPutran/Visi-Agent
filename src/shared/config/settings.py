"""
Application settings and configuration management using Pydantic
"""
import os
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# Enums for configuration
class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class StorageType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"
    AZURE = "azure"
    GCS = "gcs"
    REDIS = "redis"

class VectorDBType(str, Enum):
    FAISS = "faiss"
    PINECONE = "pinecone"
    CHROMA = "chroma"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

# 1. Environment Detection
APP_ENV_NAME = os.getenv("APP_ENV", "development").lower()
env_file_path = f".env.{APP_ENV_NAME}"

if not Path(env_file_path).exists():
    env_file_path = ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    APP_NAME: str = "Video Analytics API"
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str = Field(default= os.getenv("SECRET_KEY", "default-secret-key"))
    
    # API Settings
    API_PREFIX: str = "/api/v1"
    ENABLE_DOCS: bool = True
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    
    # CORS Settings
    CORS_ORIGINS: Union[list, List[str]] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Security
    REQUIRE_AUTH: bool = False
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_HOSTS:  List[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default= os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key")
    OPENAI_ORGANIZATION: Optional[str] = None
    OPENAI_PROJECT: Optional[str] = None
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 3
    
    # Whisper Configuration
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cuda"  # cuda, cpu
    WHISPER_COMPUTE_TYPE: str = "float16"  # float16, float32, int8
    WHISPER_BATCH_SIZE: int = 16
    WHISPER_LANGUAGE: Optional[str] = None
    
    # Vision Configuration
    VISION_MODEL: str = "gpt-4-vision-preview"
    VISION_MAX_TOKENS: int = 300
    VISION_TEMPERATURE: float = 0.1
    VISION_DETAIL_LEVEL: str = "low"  # low, high
    VISION_FRAME_INTERVAL: int = 2  # seconds
    VISION_BATCH_SIZE: int = 5
    VISION_ENABLED: bool = True
    FRAME_INTERVAL_SECONDS: int = 2  # seconds between frames to analyze
    
    # LLM Configuration
    LLM_MODEL: str = "google"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1000
    LLM_TOP_P: float = 1.0
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    
    # Storage Configuration
    STORAGE_PATH: str = "./data"
    STORAGE_VIDEO_METADATA_EXT: str = ".json"
    STORAGE_PROVIDER: str = StorageType.LOCAL # local, s3, minio, azure, gcs, redis
    QUEUE_PROVIDER: str = "redis"  # redis, in-memory, rabbitmq, etc.
    CACHE_PROVIDER: str = "redis"  # redis, in-memory, rabbitmq
    
    # S3/MinIO Configuration
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "video-analytics"
    S3_SECURE: bool = True
    
    # Azure Blob Storage
    AZURE_CONNECTION_STRING: Optional[str] = None
    AZURE_CONTAINER: str = "video-analytics"
    
    # Google Cloud Storage
    GCS_PROJECT_ID: Optional[str] = None
    GCS_BUCKET: str = "video-analytics"
    GCS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_API_KEY: str = ''
    GEMINI_API_KEY: str = ''
    
    # Vector Database Configuration
    VECTOR_DB_TYPE: VectorDBType = VectorDBType.FAISS
    VECTOR_DB_PATH: str = "./data/vectors"
    VECTOR_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    VECTOR_EMBEDDING_DIM: int = 1536
    VECTOR_SIMILARITY_METRIC: str = "cosine"
    
    # Pinecone Configuration
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX: str = "video-analytics"
    
    # Chroma Configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "video-analytics"
    
    # Qdrant Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "video-analytics"
    
    # Weaviate Configuration
    WEAVIATE_HOST: str = "localhost"
    WEAVIATE_PORT: int = 8080
    WEAVIATE_SCHEME: str = "http"
    WEAVIATE_CLASS: str = "VideoContent"
    
    # Redis Configuration
    REDIS_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PREFIX: str = "video_analytics:"
    REDIS_TTL: int = 3600  # 1 hour
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Cache Configuration
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000
    CACHE_TYPE: str = "redis"  # redis, memory
    
    # Processing Configuration
    MAX_VIDEO_SIZE_MB: int = 500
    ALLOWED_VIDEO_FORMATS: Union[list, List[str]] = ["mp4", "avi", "mov", "mkv", "webm", "flv"]
    MAX_CONCURRENT_PROCESSING: int = 3
    PROCESSING_TIMEOUT: int = 3600  # 1 hour
    TEMP_DIR: str = "./temp"
    
    # Logging Configuration
    LOG_LEVEL: LogLevel = LogLevel.DEBUG
    LOG_FORMAT: str = "json"  # json or console
    LOG_CONSOLE_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = "./logs/video-analytics.log"
    LOG_MAX_SIZE: int = 10485760  # 10 MB
    LOG_BACKUP_COUNT: int = 5
    LOG_TO_FILE: bool = True
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    
    # Job Queue
    JOB_QUEUE_ENABLED: bool = False
    JOB_QUEUE_TYPE: str = "redis"  # redis, rabbitmq, sqs
    JOB_QUEUE_URL: Optional[str] = None
    
    # Email/SMTP Configuration
    SMTP_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@video-analytics.com"
    
    # Feature Flags
    FEATURE_VISION_ANALYSIS: bool = True
    FEATURE_REALTIME_PROCESSING: bool = False
    FEATURE_BATCH_PROCESSING: bool = True
    FEATURE_WEBHOOKS: bool = False
    FEATURE_USER_AUTHENTICATION: bool = False
    
    # Validation Methods
    @field_validator("APP_ENV", mode="before")
    def validate_app_env(cls, v):
        if isinstance(v, str):
            v = v.lower()
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v
    
    
    @field_validator("ALLOWED_VIDEO_FORMATS", mode="before")
    def validate_video_formats(cls, v):
        if isinstance(v, str):
            return [fmt.strip().lower() for fmt in v.split(",")]
        return v
    
    @field_validator("STORAGE_PATH", "TEMP_DIR", "VECTOR_DB_PATH")
    def ensure_directories_exist(cls, v, values):
        """Ensure directories exist and create them if needed"""
        path = Path(v)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.APP_ENV == Environment.TESTING
    
    @property
    def openai_available(self) -> bool:
        """Check if OpenAI API key is available"""
        return bool(self.OPENAI_API_KEY)
    
    @property
    def pinecone_available(self) -> bool:
        """Check if Pinecone is configured"""
        return bool(self.PINECONE_API_KEY and self.PINECONE_ENVIRONMENT)
    
    @property
    def s3_available(self) -> bool:
        """Check if S3/MinIO is configured"""
        return bool(self.S3_ACCESS_KEY and self.S3_SECRET_KEY)
    
    @property
    def database_available(self) -> bool:
        """Check if database is configured"""
        return bool(self.DATABASE_URL)
    
    @property
    def redis_available(self) -> bool:
        """Check if Redis is configured"""
        return bool(self.REDIS_URL and self.REDIS_ENABLED)
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration based on storage type"""
        if self.STORAGE_TYPE == StorageType.S3 or self.STORAGE_TYPE == StorageType.MINIO:
            return {
                "endpoint_url": self.S3_ENDPOINT,
                "access_key": self.S3_ACCESS_KEY,
                "secret_key": self.S3_SECRET_KEY,
                "region": self.S3_REGION,
                "bucket": self.S3_BUCKET,
                "secure": self.S3_SECURE
            }
        elif self.STORAGE_TYPE == StorageType.AZURE:
            return {
                "connection_string": self.AZURE_CONNECTION_STRING,
                "container": self.AZURE_CONTAINER
            }
        elif self.STORAGE_TYPE == StorageType.GCS:
            return {
                "project_id": self.GCS_PROJECT_ID,
                "bucket": self.GCS_BUCKET,
                "credentials_path": self.GCS_CREDENTIALS_PATH
            }
        else:  # LOCAL
            return {
                "path": self.STORAGE_PATH
            }
    
    def get_vector_db_config(self) -> Dict[str, Any]:
        """Get vector database configuration"""
        if self.VECTOR_DB_TYPE == VectorDBType.PINECONE:
            return {
                "api_key": self.PINECONE_API_KEY,
                "environment": self.PINECONE_ENVIRONMENT,
                "index": self.PINECONE_INDEX
            }
        elif self.VECTOR_DB_TYPE == VectorDBType.CHROMA:
            return {
                "host": self.CHROMA_HOST,
                "port": self.CHROMA_PORT,
                "collection": self.CHROMA_COLLECTION
            }
        elif self.VECTOR_DB_TYPE == VectorDBType.QDRANT:
            return {
                "host": self.QDRANT_HOST,
                "port": self.QDRANT_PORT,
                "collection": self.QDRANT_COLLECTION
            }
        elif self.VECTOR_DB_TYPE == VectorDBType.WEAVIATE:
            return {
                "host": self.WEAVIATE_HOST,
                "port": self.WEAVIATE_PORT,
                "scheme": self.WEAVIATE_SCHEME,
                "class_name": self.WEAVIATE_CLASS
            }
        else:  # FAISS
            return {
                "path": self.VECTOR_DB_PATH
            }

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    """
    return Settings()

# Global settings instance
settings = get_settings()

# Validate settings on import
def validate_settings():
    """
    Validate critical settings and provide warnings
    """
    warnings = []
    
    if not settings.openai_available:
        warnings.append("penAI API key not set. Vision analysis and LLM features will not work.")
    
    if settings.is_production and settings.SECRET_KEY == "your-secret-key-change-in-production":
        warnings.append("Using default SECRET_KEY in production. Please change it.")
    
    if settings.is_production and settings.CORS_ORIGINS == ["*"]:
        warnings.append("CORS is set to allow all origins in production. Consider restricting.")
    
    if settings.is_production and settings.DEBUG:
        warnings.append("DEBUG mode is enabled in production. Disable for security.")
    
    if warnings:
        print("\n".join(warnings))

# Run validation when module is imported
validate_settings()