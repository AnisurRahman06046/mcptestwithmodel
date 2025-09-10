"""
MongoDB connection utilities - compatibility layer for MongoDB migration.
This module provides backward compatibility during the transition from SQLAlchemy to MongoDB.
"""

from contextlib import asynccontextmanager
from src.database.mongodb import mongodb_client
import logging

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize MongoDB connection - compatibility function"""
    return await mongodb_client.connect()


@asynccontextmanager
async def get_db_context():
    """Context manager for MongoDB operations - compatibility function"""
    if not mongodb_client.is_connected:
        await mongodb_client.connect()
    
    try:
        yield mongodb_client.database
    except Exception as e:
        logger.error(f"Database operation error: {e}")
        raise