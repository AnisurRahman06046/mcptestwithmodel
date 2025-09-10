"""
Application startup orchestration.
Coordinates the initialization of various application components.
"""

import logging
from typing import List, Callable, Any
from src.database.manager import database_manager
from src.config import settings

logger = logging.getLogger(__name__)


class StartupOrchestrator:
    """
    Orchestrates application startup sequence following clean architecture.
    """
    
    def __init__(self):
        self._startup_tasks: List[Callable] = []
        self._shutdown_tasks: List[Callable] = []
        self._is_started = False
        
    def add_startup_task(self, task: Callable, name: str = None):
        """Add a startup task to the orchestrator."""
        self._startup_tasks.append((task, name or task.__name__))
        
    def add_shutdown_task(self, task: Callable, name: str = None):
        """Add a shutdown task to the orchestrator."""
        self._shutdown_tasks.append((task, name or task.__name__))
        
    async def startup(self) -> bool:
        """
        Execute startup sequence for all application components.
        
        Returns:
            bool: True if all startup tasks successful
        """
        if self._is_started:
            logger.warning("Application already started")
            return True
            
        logger.info("🚀 Starting E-commerce MCP Server")
        logger.info(f"📊 Server Configuration:")
        logger.info(f"   - Host: {settings.HOST}:{settings.PORT}")
        logger.info(f"   - Debug Mode: {settings.DEBUG}")
        logger.info(f"   - Log Level: {settings.LOG_LEVEL}")
        
        # Execute database initialization
        try:
            logger.info("🔌 Connecting to MongoDB Atlas...")
            success = await database_manager.initialize()
            
            if not success:
                logger.error("❌ Database initialization failed")
                return False
                
            logger.info("✅ Database connection established successfully!")
            
            # Seed data if configured
            if settings.SEED_DATABASE:
                logger.info("🌱 Seeding database with mock data...")
                seed_success = await database_manager.seed_data()
                
                if seed_success:
                    logger.info("✅ Database seeded successfully!")
                else:
                    logger.warning("⚠️ Database seeding completed with warnings")
                    
        except Exception as e:
            logger.error(f"❌ Startup failed during database initialization: {e}")
            return False
        
        # Execute additional startup tasks
        for task, name in self._startup_tasks:
            try:
                logger.info(f"Executing startup task: {name}")
                if callable(task):
                    result = await task() if hasattr(task, '__await__') else task()
                    if result is False:
                        logger.error(f"Startup task failed: {name}")
                        return False
                        
            except Exception as e:
                logger.error(f"Startup task '{name}' failed: {e}", exc_info=True)
                return False
        
        self._is_started = True
        logger.info("🎉 E-commerce MCP Server started successfully!")
        logger.info(f"📖 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
        
        return True
        
    async def shutdown(self) -> bool:
        """
        Execute shutdown sequence for all application components.
        
        Returns:
            bool: True if all shutdown tasks successful
        """
        if not self._is_started:
            logger.info("Application not started, skipping shutdown")
            return True
            
        logger.info("⏳ Shutting down E-commerce MCP Server...")
        
        # Execute custom shutdown tasks first
        for task, name in reversed(self._shutdown_tasks):
            try:
                logger.info(f"Executing shutdown task: {name}")
                if callable(task):
                    await task() if hasattr(task, '__await__') else task()
                    
            except Exception as e:
                logger.error(f"Shutdown task '{name}' failed: {e}", exc_info=True)
        
        # Database cleanup
        try:
            logger.info("🔌 Closing database connections...")
            await database_manager.cleanup()
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}", exc_info=True)
        
        self._is_started = False
        logger.info("✅ Server shutdown completed!")
        
        return True
        
    @property
    def is_started(self) -> bool:
        """Check if application is started."""
        return self._is_started


# Global startup orchestrator instance
startup_orchestrator = StartupOrchestrator()