"""
Sync-specific configuration settings.
Extends the main settings with MySQL and sync configuration.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class SyncSettings(BaseSettings):
    """Configuration for MySQL-MongoDB sync system."""
    
    # MySQL Database Configuration
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str
    MYSQL_CHARSET: str = "utf8mb4"
    
    # MySQL Connection Pool Settings
    MYSQL_MIN_POOL_SIZE: int = 1
    MYSQL_MAX_POOL_SIZE: int = 10
    MYSQL_POOL_TIMEOUT: int = 30
    MYSQL_POOL_RECYCLE: int = 3600
    
    # Sync Settings
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL_MINUTES: int = 60
    SYNC_BATCH_SIZE: int = 1000
    SYNC_MAX_RETRIES: int = 3
    SYNC_RETRY_DELAY: int = 30
    
    # Table Configuration (can be auto-discovered)
    SYNC_TABLES: Optional[List[str]] = None  # None means auto-discover all tables
    SYNC_ONLY_TIMESTAMP_TABLES: bool = True  # Only sync tables with timestamp columns
    
    # MongoDB Sync Collections Mapping
    # These map MySQL table names to MongoDB collection names
    TABLE_TO_COLLECTION_MAPPING: dict = {
        # Will be populated dynamically based on discovered tables
        # Example: "products": "products", "users": "customers"
    }
    
    # Sync Control
    SYNC_AUTO_START: bool = False  # Don't auto-start sync on startup
    SYNC_REQUIRE_APPROVAL: bool = True  # Require manual approval before first sync
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create sync settings instance
sync_settings = SyncSettings()

# Create required directories
os.makedirs("logs/sync", exist_ok=True)