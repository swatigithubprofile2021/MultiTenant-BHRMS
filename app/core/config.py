from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import os 
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_USERNAME = os.getenv("OLLAMA_USERNAME")
OLLAMA_PASSWORD = os.getenv("OLLAMA_PASSWORD")

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and .env file.
    """
    
    ##Ollama Configuration
    

    # Paths
    UPLOAD_DIR: Path = Path("./uploads")
    LOG_PATH: Path = Path("./logs")

    ##Upload limits
    MAX_UPLOAD_SIZE_DOCUMENT: int = 50 * 1024 * 1024  # 10MB
    MAX_UPLOAD_SIZE: int = 2 * 1024 * 1024  # 2MB

    # Embedding Model (Open Source)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDDING_DIMEN: int
    RERANK_MODEL: str = "BAAI/bge-reranker-base"
    # Alternative: "sentence-transformers/all-MiniLM-L6-v2" (faster, 384 dims)
    # Alternative: "BAAI/bge-large-en-v1.5" (high quality, 1024 dims)

    # LLM Configuration (Open Source via Ollama or local)
    LLM_MODEL: str = "qwen2.5:1.5b"  # Can be swapped with any local/Ollama model
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKEN_LIMIT: int = 200

    # Maximum number of CPU cores the model is allowed to use for computation
    LLM_MAX_NUM_THREAD: int = 2

    # Chunking Strategy
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Retrieval
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_CUTOFF: float = 0.7

    # Redis for caching and Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SEMANTIC_CACHE_TTL: int = 3600
    REDIS_SEMANTIC_DISTANCE_THRES: float = 0.2

    # For Chat history
    CHAT_HISTORY_TTL: int = 3600
    CHAT_HISTORY_LENGTH: int = 10

    # API Security
    JWT_SECRET: str
    JWT_ALGO: str
    JWT_TOKEN_EXPIRE_MINUTES: int
    API_RATE_LIMIT: int = 100  # requests per minute

    # DB Url
    ASYNC_DATABASE_URL: str
    SYNC_DATABASE_URL: str

    DB_POOL_SIZE: int = 20
    DB_TIMEOUT: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignores variables in .env not defined in the model
    )


# Instantiate the settings object
settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_PATH.mkdir(parents=True, exist_ok=True)
