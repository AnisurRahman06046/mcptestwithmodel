"""
Database lifecycle management.
Handles database connection, initialization, and cleanup operations.
"""

import logging
from typing import Optional
from src.database.mongodb import mongodb_client
from src.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database lifecycle operations following clean architecture principles.
    """
    
    def __init__(self):
        self._is_initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize database connections and perform setup operations.
        
        Returns:
            bool: True if initialization successful
        """
        if self._is_initialized:
            logger.warning("Database already initialized")
            return True
            
        try:
            logger.info("Initializing MongoDB connection")
            success = await mongodb_client.connect()
            
            if not success:
                logger.error("Failed to establish MongoDB connection")
                return False
                
            logger.info(f"Successfully connected to MongoDB database: {settings.DB_NAME}")
            
            # Perform health check
            health_status = await mongodb_client.health_check()
            if health_status.get("status") != "healthy":
                logger.warning(f"Database health check warning: {health_status}")
            
            self._is_initialized = True
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            return False
    
    async def seed_data(self) -> bool:
        """
        Seed database with initial/mock data if configured.
        
        Returns:
            bool: True if seeding successful or not needed
        """
        if not settings.SEED_DATABASE:
            logger.info("Database seeding disabled in configuration")
            return True
            
        if not self._is_initialized:
            logger.error("Cannot seed data: Database not initialized")
            return False
            
        try:
            logger.info("Starting database seeding process")
            
            from src.database.seeder import mongodb_seeder
            success = await mongodb_seeder.seed_all()
            
            if success:
                logger.info("Database seeding completed successfully")
            else:
                logger.warning("Database seeding completed with warnings")
                
            return success
            
        except Exception as e:
            logger.error(f"Database seeding failed: {e}", exc_info=True)
            return False
    
    async def cleanup(self) -> bool:
        """
        Clean up database connections and resources.
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            if self._is_initialized:
                logger.info("Cleaning up database connections")
                await mongodb_client.disconnect()
                self._is_initialized = False
                logger.info("Database cleanup completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}", exc_info=True)
            return False
    
    async def health_check(self) -> dict:
        """
        Perform comprehensive database health check.
        
        Returns:
            dict: Health check results
        """
        if not self._is_initialized:
            return {
                "status": "not_initialized",
                "message": "Database manager not initialized"
            }
            
        try:
            return await mongodb_client.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._is_initialized
    
    @property
    def database(self):
        """Get database instance."""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized")
        return mongodb_client.database


# Global database manager instance
database_manager = DatabaseManager()