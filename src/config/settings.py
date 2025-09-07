from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./data/database/ecommerce.db"
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()

# Ensure data directories exist
os.makedirs("data/database", exist_ok=True)
os.makedirs("data/models", exist_ok=True)
os.makedirs("logs", exist_ok=True)