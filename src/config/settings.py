from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # MongoDB Configuration
    ATLAS_URI: str = "mongodb+srv://anisurrahman14046_db_user:teAl7rZGMGq12JkX@ppnur.9knhsjp.mongodb.net"
    DB_NAME: str = "ppnur"
    MONGODB_MIN_POOL_SIZE: int = 1
    MONGODB_MAX_POOL_SIZE: int = 5  # Reduced for development
    MONGODB_MAX_IDLE_TIME_MS: int = 60000  # Increased idle time
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 10000  # Increased timeout
    MONGODB_CONNECT_TIMEOUT_MS: int = 10000
    MONGODB_SOCKET_TIMEOUT_MS: int = 30000
    
    # Model Configuration
    MODEL_PATH: str = "./data/models"
    DEFAULT_MODEL: str = "llama3-7b"
    MODEL_CONTEXT_SIZE: int = 4096
    MODEL_THREADS: int = 4
    MODEL_GPU_LAYERS: int = 35
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = 5
    QUERY_TIMEOUT: int = 30
    MODEL_LOAD_TIMEOUT: int = 60
    
    # Mock Data Settings
    SEED_DATABASE: bool = True
    MOCK_USER_COUNT: int = 100
    MOCK_PRODUCT_COUNT: int = 50
    MOCK_ORDER_COUNT: int = 200
    
    # MySQL Sync Configuration (optional - for sync feature)
    MYSQL_HOST: Optional[str] = None
    MYSQL_PORT: int = 3306
    MYSQL_USER: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_DATABASE: Optional[str] = None
    MYSQL_CHARSET: str = "utf8mb4"
    
    # Sync Settings
    SYNC_ENABLED: bool = False  # Disabled by default
    SYNC_INTERVAL_MINUTES: int = 60
    SYNC_BATCH_SIZE: int = 1000
    SYNC_ONLY_TIMESTAMP_TABLES: bool = True
    SYNC_AUTO_START: bool = False
    SYNC_TABLES: Optional[str] = None  # Comma-separated table names
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()

# Ensure data directories exist
os.makedirs("data/models", exist_ok=True)
os.makedirs("logs", exist_ok=True)