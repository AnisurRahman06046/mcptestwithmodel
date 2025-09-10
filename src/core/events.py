"""
FastAPI lifespan event handlers.
Clean separation of application lifecycle events.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.startup import startup_orchestrator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles application startup and shutdown events cleanly.
    """
    # Startup sequence
    try:
        startup_success = await startup_orchestrator.startup()
        
        if not startup_success:
            logger.error("Application startup failed")
            raise RuntimeError("Failed to start application")
            
    except Exception as e:
        logger.error(f"Critical startup error: {e}", exc_info=True)
        raise
    
    # Application is running
    yield
    
    # Shutdown sequence  
    try:
        await startup_orchestrator.shutdown()
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


def configure_startup_tasks():
    """
    Configure additional startup tasks if needed.
    This function can be extended to add more startup tasks.
    """
    # Example of adding custom startup tasks:
    # startup_orchestrator.add_startup_task(initialize_cache, "cache_initialization")
    # startup_orchestrator.add_startup_task(load_models, "model_loading")
    pass


def configure_shutdown_tasks():
    """
    Configure additional shutdown tasks if needed.
    This function can be extended to add more shutdown tasks.
    """
    # Example of adding custom shutdown tasks:
    # startup_orchestrator.add_shutdown_task(cleanup_cache, "cache_cleanup")
    # startup_orchestrator.add_shutdown_task(save_metrics, "metrics_save")
    pass