"""
MongoDB connection and client management for MongoDB Atlas.
Clean implementation focused on connection and basic operations.
"""

import logging
from typing import Optional, Dict, Any
from pymongo import AsyncMongoClient
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError, 
    ConfigurationError
)
from src.config import settings

logger = logging.getLogger(__name__)

# Suppress MongoDB background task warnings
logging.getLogger("pymongo.client").setLevel(logging.CRITICAL)
logging.getLogger("pymongo.topology").setLevel(logging.CRITICAL)
logging.getLogger("pymongo.pool").setLevel(logging.CRITICAL)


class MongoDBClient:
    """
    MongoDB Atlas client with connection pooling and error handling.
    """
    
    def __init__(self):
        self._client: Optional[AsyncMongoClient] = None
        self._database = None
        self._is_connected = False
        
    async def connect(self) -> bool:
        """
        Establish connection to MongoDB Atlas.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self._is_connected:
            logger.info("MongoDB client already connected")
            return True
            
        try:
            logger.info("Connecting to MongoDB Atlas...")
            
            # Create client with optimized Atlas configuration
            self._client = AsyncMongoClient(
                settings.ATLAS_URI,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                maxIdleTimeMS=settings.MONGODB_MAX_IDLE_TIME_MS,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
                socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS,
                retryWrites=True,
                retryReads=True,
                # Additional settings to reduce connection pool issues
                maxConnecting=2,
                waitQueueTimeoutMS=5000,
                heartbeatFrequencyMS=30000  # Reduce heartbeat frequency
            )
            
            # Test the connection
            await self._client.admin.command("ping")
            
            # Get database reference
            self._database = self._client[settings.DB_NAME]
            
            self._is_connected = True
            
            logger.info(f"Successfully connected to MongoDB Atlas database: {settings.DB_NAME}")
            return True
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            return False
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failure: {e}")
            return False
            
        except ConfigurationError as e:
            logger.error(f"MongoDB configuration error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}", exc_info=True)
            return False
    
    async def disconnect(self):
        """Gracefully disconnect from MongoDB."""
        if self._client:
            logger.info("Disconnecting from MongoDB...")
            await self._client.close()
            self._client = None
            self._database = None
            self._is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for MongoDB connection.
        
        Returns:
            Dict containing health status
        """
        if not self._is_connected or not self._client:
            return {
                "status": "disconnected",
                "connected": False,
                "error": "No active connection"
            }
        
        try:
            # Test basic connectivity
            await self._client.admin.command("ping")
            
            return {
                "status": "healthy",
                "connected": True,
                "database": settings.DB_NAME
            }
            
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    @property
    def database(self):
        """Get the database instance."""
        if not self._is_connected:
            raise RuntimeError("MongoDB client not connected. Call connect() first.")
        return self._database
    
    @property
    def client(self) -> AsyncMongoClient:
        """Get the client instance."""
        if not self._is_connected:
            raise RuntimeError("MongoDB client not connected. Call connect() first.")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected


# Global MongoDB client instance
mongodb_client = MongoDBClient()


async def init_database():
    """Initialize MongoDB connection."""
    logger.info("Initializing MongoDB database...")
    
    success = await mongodb_client.connect()
    if not success:
        raise RuntimeError("Failed to connect to MongoDB Atlas")
    
    logger.info("MongoDB database initialized successfully")


async def close_database():
    """Close MongoDB connection gracefully."""
    await mongodb_client.disconnect()


def get_database():
    """Get database instance for synchronous operations."""
    return mongodb_client.database