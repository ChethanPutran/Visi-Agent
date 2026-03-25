"""
Application settings and configuration management using Pydantic
"""
import os
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pathlib import Path
from pydantic import Field, field_validator, SecretStr, computed_field, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Enums for configuration
class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class StorageProviders(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"
    AZURE = "azure"
    GCS = "gcs"
    REDIS = "redis"

class CacheProviders(str, Enum):
    LOCAL = "local"
    REDIS = "redis"

class QueueProviders(str, Enum):
    LOCAL = "local"
    REDIS = "redis"

class VectorDBType(str, Enum):
    FAISS = "faiss"
    PINECONE = "pinecone"
    CHROMA = "chroma"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"

class LLMModels(str, Enum):
    GEMINI = "gemini-3-flash-preview"
    GPT4 = "gpt-4"

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'development').lower()}",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # --- Application ---
    APP_NAME: str = "Video Analytics API"
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_WORKERS: int = 4
    VIDEO_SERVICE_WORKERS: int = 3
    DEBUG: bool = True
    SECRET_KEY: SecretStr = Field(default=SecretStr("dev-secret-key-change-me"), validation_alias="SECRET_KEY")
    
    # --- Security ---
    REQUIRE_AUTH: bool = False
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_HOSTS: List[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60 # seconds
    
    # --- Infrastructure Providers ---
    STORAGE_PROVIDER: StorageProviders = StorageProviders.LOCAL # local,  s3, minio, azure, gcs, redis
    QUEUE_PROVIDER: QueueProviders = QueueProviders.LOCAL # local, redis
    QUEUE_NAME: str = "video_queue"
    CACHE_PROVIDER: CacheProviders = CacheProviders.LOCAL # local, redis
    STORAGE_PATH: str = "./data/storage"
    TEMP_DIR: str = "./temp"
    STORAGE_PATH: str = "./data"
    CACHE_STORAGE_PATH: str = "./data/cache"
    STORAGE_VIDEO_METADATA_EXT: str = ".json"

    # --- API Keys ---
    OPENAI_API_KEY: Optional[SecretStr] = Field(None, validation_alias="OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[SecretStr] = Field(None, validation_alias="GEMINI_API_KEY")

    # --- Whisper (Auto-detect CUDA for IISc CDS Servers) ---
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cuda" if os.path.exists("/dev/nvidia0") else "cpu"
    
    # --- Vector DB ---
    VECTOR_PROVIDER: VectorDBType = VectorDBType.FAISS
    VECTOR_DB_PATH: str = "./data/vectors"

    # --- Pinecone Configuration ---
    PINECONE_API_KEY: Optional[SecretStr] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None

    # --- Chroma Configuration ---
    CHROMA_PERSISTENT_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "default_collection"
    CHROMA_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2" # This is a common sentence transformer model, adjust as needed

    # --- S3 / Minio Configuration ---
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[SecretStr] = None
    S3_SECRET_KEY: Optional[SecretStr] = None
    S3_BUCKET: str = "video-analytics"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = True

    # --- LLM Configuration ---
    LLM_MODEL: LLMModels = LLMModels.GEMINI
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1000
    LLM_TOP_P: float = 1.0
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    LLM_MAX_RETRIES: int = 2

    # --- Vision Configuration ---
    VISION_MODEL: str = "gpt-4-vision-preview"
    VISION_MAX_TOKENS: int = 300
    VISION_TEMPERATURE: float = 0.1
    VISION_DETAIL_LEVEL: str = "low" # low, high
    VISION_FRAME_INTERVAL: int = 2 # seconds
    VISION_BATCH_SIZE: int = 5
    VISION_ENABLED: bool = True
    FRAME_INTERVAL_SECONDS: int = 2 # seconds

    # --- Query Service Configuration ---
    QUERY_INCLUDE_TIMESTAMPS: bool = True
    QUERY_MAX_RESULTS: int = 5
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DECODE_RESPONSES: bool = True

    # --- Logging Configuration ---
    LOG_LEVEL: LogLevel = LogLevel.DEBUG
    LOG_FORMAT: str = "json" # json or console
    LOG_CONSOLE_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = "./logs/video-analytics.log"
    LOG_MAX_SIZE: int = 10485760 # 10 MB
    LOG_BACKUP_COUNT: int = 5
    LOG_TO_FILE: bool = True

    # --- Documentation ---
    ENABLE_DOCS: bool = True

    # --- CORS Settings ---
    CORS_ORIGINS: Any = ["*"] 
    

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            # Clean up the string from .env
            v = v.strip().strip('"').strip("'")
            if not v or v == "*":
                return ["*"]
            # Split the comma-separated string into a real list
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Do the same for METHODS and HEADERS if they are in your .env
    CORS_ALLOW_METHODS: Any = ["*"]
    CORS_ALLOW_HEADERS: Any = ["*"]

    @field_validator("CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def parse_comma_lists(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip().strip('"').strip("'")
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

  

    @field_validator("S3_ENDPOINT", mode="after")
    @classmethod
    def check_s3_config(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Ensure Endpoint is present if Storage is set to S3"""
        if info.data.get("STORAGE_PROVIDER") in [StorageType.S3, StorageType.MINIO] and not v:
            raise ValueError("S3_ENDPOINT must be provided when using S3/MinIO storage")
        return v

    @field_validator("STORAGE_PATH", "TEMP_DIR", "VECTOR_DB_PATH", mode="after")
    @classmethod
    def ensure_directories_exist(cls, v: str) -> str:
        """Bootstrap directories on startup"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
   

    @computed_field
    @property
    def is_local(self) -> bool:
        return self.STORAGE_PROVIDER == StorageType.LOCAL

    # --- Helper Properties ---
    @property
    def gemini_available(self) -> bool:
        return self.GEMINI_API_KEY is not None
    
    # --- Helper Properties ---
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == Environment.DEVELOPMENT

# Global cache for settings to avoid re-reading .env files

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

    if not settings.gemini_available:
        warnings.append("GEMINI_API_KEY not set. Vision analysis and LLM features will not work.")
    
    if settings.is_development:
        print("Development environment detected.")

    if warnings:
        print("\n".join(warnings))

# Run validation when module is imported
validate_settings()