"""
Sync timestamp tracking system.
Manages last sync times for incremental data synchronization.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class SyncTracker:
    """
    Tracks last sync timestamps for each table to enable incremental sync.
    Stores sync metadata in MongoDB for persistence across restarts.
    """
    
    def __init__(self):
        self.db = None
        self.collection_name = "sync_metadata"
        self._cache: Dict[str, datetime] = {}
    
    async def initialize(self, database):
        """Initialize the sync tracker with MongoDB database."""
        self.db = database
        
        # Ensure collection exists and create index
        collection = self.db[self.collection_name]
        await collection.create_index("table_name", unique=True)
        
        # Load existing sync times into cache
        await self._load_cache()
        
        logger.info("Sync tracker initialized")
    
    async def _load_cache(self):
        """Load all sync times into memory cache for faster access."""
        if self.db is None:
            return
        
        collection = self.db[self.collection_name]
        
        async for doc in collection.find({}):
            table_name = doc["table_name"]
            last_sync = doc["last_sync_time"]
            self._cache[table_name] = last_sync
        
        logger.info(f"Loaded {len(self._cache)} sync timestamps into cache")
    
    async def get_last_sync_time(self, table_name: str) -> Optional[datetime]:
        """
        Get the last sync timestamp for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Last sync datetime or None if never synced
        """
        # Check cache first
        if table_name in self._cache:
            return self._cache[table_name]
        
        # If not in cache, check database
        if self.db is None:
            return None
        
        collection = self.db[self.collection_name]
        doc = await collection.find_one({"table_name": table_name})
        
        if doc:
            last_sync = doc["last_sync_time"]
            self._cache[table_name] = last_sync
            return last_sync
        
        return None
    
    async def update_last_sync_time(
        self, 
        table_name: str, 
        sync_time: Optional[datetime] = None
    ):
        """
        Update the last sync timestamp for a table.
        
        Args:
            table_name: Name of the table
            sync_time: Sync timestamp (defaults to current UTC time)
        """
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)
        
        if self.db is None:
            logger.warning("Database not initialized, cannot update sync time")
            return
        
        collection = self.db[self.collection_name]
        
        # Update in database
        await collection.replace_one(
            {"table_name": table_name},
            {
                "table_name": table_name,
                "last_sync_time": sync_time,
                "updated_at": datetime.now(timezone.utc)
            },
            upsert=True
        )
        
        # Update cache
        self._cache[table_name] = sync_time
        
        logger.debug(f"Updated sync time for {table_name}: {sync_time}")
    
    async def get_all_sync_times(self) -> Dict[str, datetime]:
        """Get all sync timestamps for all tables."""
        if self.db is None:
            return self._cache.copy()
        
        # Ensure cache is up to date
        await self._load_cache()
        return self._cache.copy()
    
    async def reset_sync_time(self, table_name: str):
        """
        Reset sync time for a table (force full sync on next run).
        
        Args:
            table_name: Name of the table
        """
        if self.db is None:
            logger.warning("Database not initialized, cannot reset sync time")
            return
        
        collection = self.db[self.collection_name]
        
        # Remove from database
        await collection.delete_one({"table_name": table_name})
        
        # Remove from cache
        self._cache.pop(table_name, None)
        
        logger.info(f"Reset sync time for {table_name}")
    
    async def reset_all_sync_times(self):
        """Reset all sync times (force full sync for all tables)."""
        if self.db is None:
            logger.warning("Database not initialized, cannot reset sync times")
            return
        
        collection = self.db[self.collection_name]
        
        # Clear database
        await collection.delete_many({})
        
        # Clear cache
        self._cache.clear()
        
        logger.info("Reset all sync times")
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """Get sync statistics and metadata."""
        if self.db is None:
            return {
                "total_tables_tracked": len(self._cache),
                "tables": {}
            }
        
        collection = self.db[self.collection_name]
        
        # Get all sync records with additional metadata
        stats = {
            "total_tables_tracked": 0,
            "tables": {},
            "oldest_sync": None,
            "newest_sync": None
        }
        
        oldest_sync = None
        newest_sync = None
        
        async for doc in collection.find({}):
            table_name = doc["table_name"]
            last_sync = doc["last_sync_time"]
            updated_at = doc.get("updated_at")
            
            # Ensure timezone awareness for datetime comparison
            if last_sync and last_sync.tzinfo is None:
                # Make naive datetime timezone-aware (assuming UTC)
                last_sync = last_sync.replace(tzinfo=timezone.utc)

            stats["tables"][table_name] = {
                "last_sync_time": last_sync.isoformat() if last_sync else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "days_since_sync": (datetime.now(timezone.utc) - last_sync).days if last_sync else None
            }
            
            # Track oldest and newest sync times
            if last_sync:
                if not oldest_sync or last_sync < oldest_sync:
                    oldest_sync = last_sync
                if not newest_sync or last_sync > newest_sync:
                    newest_sync = last_sync
        
        stats["total_tables_tracked"] = len(stats["tables"])
        stats["oldest_sync"] = oldest_sync.isoformat() if oldest_sync else None
        stats["newest_sync"] = newest_sync.isoformat() if newest_sync else None
        
        return stats
    
    async def cleanup_old_metadata(self, days_old: int = 30):
        """
        Clean up metadata for tables that haven't been synced in a while.
        
        Args:
            days_old: Remove metadata for tables not synced in this many days
        """
        if self.db is None:
            logger.warning("Database not initialized, cannot cleanup metadata")
            return
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        collection = self.db[self.collection_name]
        
        # Find old records
        old_records = await collection.find(
            {"last_sync_time": {"$lt": cutoff_date}}
        ).to_list(None)
        
        if not old_records:
            logger.info("No old sync metadata to cleanup")
            return
        
        # Remove old records
        result = await collection.delete_many(
            {"last_sync_time": {"$lt": cutoff_date}}
        )
        
        # Update cache
        for record in old_records:
            table_name = record["table_name"]
            self._cache.pop(table_name, None)
        
        logger.info(f"Cleaned up {result.deleted_count} old sync metadata records")
    
    def get_cached_sync_times(self) -> Dict[str, datetime]:
        """Get sync times from cache (no database access)."""
        return self._cache.copy()
    
    async def force_cache_refresh(self):
        """Force refresh of the cache from database."""
        self._cache.clear()
        await self._load_cache()
        logger.info("Sync tracker cache refreshed from database")