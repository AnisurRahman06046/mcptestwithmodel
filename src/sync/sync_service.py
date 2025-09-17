"""
Main sync orchestration service.
Coordinates the entire sync process between MySQL and MongoDB.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from .mysql_connector import MySQLConnector, MySQLConnectionConfig, TableInfo
from .data_mapper import DataMapper  # Keep old mapper for backward compatibility
from .dynamic_data_mapper import DynamicDataMapper  # New schema-less mapper
from .sync_tracker import SyncTracker
from ..database.mongodb import mongodb_client
from ..config.settings import settings

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Sync operation status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class TableSyncResult:
    """Result of syncing a single table."""
    table_name: str
    success: bool
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a complete sync operation."""
    sync_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SyncStatus = SyncStatus.RUNNING
    tables_synced: List[TableSyncResult] = None
    total_records: int = 0
    total_errors: int = 0
    duration_seconds: float = 0.0
    
    def __post_init__(self):
        if self.tables_synced is None:
            self.tables_synced = []


class SyncService:
    """
    Main synchronization service that orchestrates data flow
    from MySQL to MongoDB with error handling and monitoring.
    """
    
    def __init__(self):
        self.mysql_connector: Optional[MySQLConnector] = None
        # Use dynamic mapper by default for schema-less sync
        self.use_dynamic_mapper = getattr(settings, 'USE_DYNAMIC_SYNC', True)
        if self.use_dynamic_mapper:
            self.data_mapper = DynamicDataMapper()
            logger.info("Using DynamicDataMapper for schema-less sync")
        else:
            self.data_mapper = DataMapper()
            logger.info("Using legacy DataMapper with predefined schemas")
        self.sync_tracker = SyncTracker()
        self.mongodb = None
        self.status = SyncStatus.IDLE
        self.current_sync: Optional[SyncResult] = None
        self._stop_requested = False
    
    async def initialize(self) -> bool:
        """Initialize all components needed for sync."""
        try:
            # Initialize MySQL connector
            mysql_config = MySQLConnectionConfig(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                charset=settings.MYSQL_CHARSET
            )
            
            self.mysql_connector = MySQLConnector(mysql_config)
            if not await self.mysql_connector.connect():
                logger.error("Failed to connect to MySQL")
                return False
            
            # Initialize MongoDB
            self.mongodb = mongodb_client.database
            
            # Initialize sync tracker
            await self.sync_tracker.initialize(self.mongodb)
            
            logger.info("Sync service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sync service: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all connections and cleanup."""
        if self.mysql_connector:
            await self.mysql_connector.disconnect()
        logger.info("Sync service shutdown complete")
    
    async def discover_sync_tables(self) -> Dict[str, TableInfo]:
        """Discover which tables should be synced based on configuration."""
        if not self.mysql_connector:
            raise RuntimeError("MySQL connector not initialized")
        
        # Check and reconnect if needed
        if not self.mysql_connector.is_connected:
            logger.warning("MySQL connection lost, reconnecting...")
            if not await self.mysql_connector.connect():
                raise RuntimeError("Failed to reconnect to MySQL")
        
        # Discover all tables first
        try:
            all_tables = await self.mysql_connector.discover_all_tables()
        except Exception as e:
            logger.error(f"Error discovering tables, attempting to reconnect: {e}")
            # Try to reconnect and retry once
            if await self.mysql_connector.connect():
                all_tables = await self.mysql_connector.discover_all_tables()
            else:
                raise
        
        # If specific tables are configured, use those
        if hasattr(settings, 'SYNC_TABLES') and settings.SYNC_TABLES:
            # Parse comma-separated table names
            table_names = [name.strip() for name in settings.SYNC_TABLES.split(',')]
            sync_tables = {}
            for table_name in table_names:
                if table_name in all_tables:
                    sync_tables[table_name] = all_tables[table_name]
                else:
                    logger.warning(f"Configured table '{table_name}' not found in database")
            return sync_tables
        
        # Otherwise, use timestamp-enabled tables if configured
        if getattr(settings, 'SYNC_ONLY_TIMESTAMP_TABLES', True):
            return await self.mysql_connector.get_tables_with_timestamps()
        
        # Default: return all tables
        return all_tables
    
    async def sync_all_tables(self) -> SyncResult:
        """Sync all configured tables from MySQL to MongoDB."""
        if self.status == SyncStatus.RUNNING:
            raise RuntimeError("Sync is already running")
        
        sync_id = f"sync_{int(datetime.now(timezone.utc).timestamp())}"
        self.current_sync = SyncResult(
            sync_id=sync_id,
            start_time=datetime.now(timezone.utc)
        )
        self.status = SyncStatus.RUNNING
        self._stop_requested = False
        
        logger.info(f"Starting sync operation: {sync_id}")
        
        try:
            # Discover tables to sync
            tables_to_sync = await self.discover_sync_tables()
            
            if not tables_to_sync:
                logger.warning("No tables found to sync")
                self.current_sync.status = SyncStatus.COMPLETED
                return self.current_sync
            
            logger.info(f"Syncing {len(tables_to_sync)} tables: {list(tables_to_sync.keys())}")
            
            # Sync each table
            for table_name, table_info in tables_to_sync.items():
                if self._stop_requested:
                    logger.info("Sync stop requested, aborting")
                    break
                
                table_result = await self.sync_table(table_name, table_info)
                self.current_sync.tables_synced.append(table_result)
                
                # Update totals
                self.current_sync.total_records += table_result.records_processed
                self.current_sync.total_errors += table_result.errors
            
            # Mark as completed
            self.current_sync.end_time = datetime.now(timezone.utc)
            self.current_sync.duration_seconds = (
                self.current_sync.end_time - self.current_sync.start_time
            ).total_seconds()
            
            if self._stop_requested:
                self.current_sync.status = SyncStatus.PAUSED
            elif self.current_sync.total_errors > 0:
                self.current_sync.status = SyncStatus.ERROR
            else:
                self.current_sync.status = SyncStatus.COMPLETED
            
            self.status = SyncStatus.IDLE
            
            logger.info(f"Sync completed: {self.current_sync.status.value}")
            logger.info(f"  Records processed: {self.current_sync.total_records}")
            logger.info(f"  Errors: {self.current_sync.total_errors}")
            logger.info(f"  Duration: {self.current_sync.duration_seconds:.2f}s")
            
            return self.current_sync
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.current_sync.status = SyncStatus.ERROR
            self.current_sync.end_time = datetime.now(timezone.utc)
            self.status = SyncStatus.IDLE
            raise
    
    async def sync_table(self, table_name: str, table_info: TableInfo) -> TableSyncResult:
        """Sync a specific table from MySQL to MongoDB."""
        start_time = datetime.now(timezone.utc)
        result = TableSyncResult(table_name=table_name, success=False)
        
        logger.info(f"Starting sync for table: {table_name}")
        
        try:
            # Get last sync time for this table
            last_sync = await self.sync_tracker.get_last_sync_time(table_name)
            logger.info(f"  Last sync: {last_sync or 'Never'}")
            
            # Get incremental data from MySQL
            mysql_data = await self.mysql_connector.get_incremental_data(
                table_name, 
                last_sync, 
                getattr(settings, 'SYNC_BATCH_SIZE', 1000)
            )
            
            logger.info(f"  Fetched {len(mysql_data)} records from MySQL")
            
            if not mysql_data:
                logger.info(f"  No new data to sync for {table_name}")
                result.success = True
                return result
            
            # Transform data for MongoDB
            mongodb_data = await self.data_mapper.transform_table_data(
                mysql_data, table_name, table_info
            )
            
            # Determine target collection name  
            collection_name = table_name  # Use table name as collection name
            
            # Insert/update data in MongoDB
            collection = self.mongodb[collection_name]
            
            records_created = 0
            records_updated = 0
            errors = 0
            
            for record in mongodb_data:
                try:
                    # Use upsert to handle both inserts and updates
                    if '_id' in record:
                        filter_query = {'_id': record['_id']}
                    else:
                        # Use a combination of fields as identifier
                        filter_query = self._build_filter_query(record, table_info)
                    
                    result_op = await collection.replace_one(
                        filter_query, 
                        record, 
                        upsert=True
                    )
                    
                    if result_op.upserted_id:
                        records_created += 1
                    elif result_op.modified_count > 0:
                        records_updated += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing record: {e}")
                    errors += 1
            
            # Update sync timestamp
            await self.sync_tracker.update_last_sync_time(table_name)
            
            # Calculate results
            end_time = datetime.now(timezone.utc)
            result.success = True
            result.records_processed = len(mongodb_data)
            result.records_created = records_created
            result.records_updated = records_updated
            result.errors = errors
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"  Sync completed for {table_name}:")
            logger.info(f"    Created: {records_created}")
            logger.info(f"    Updated: {records_updated}")
            logger.info(f"    Errors: {errors}")
            logger.info(f"    Duration: {result.duration_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to sync table {table_name}: {e}")
            result.error_message = str(e)
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
        
        return result
    
    def _build_filter_query(self, record: Dict[str, Any], table_info: TableInfo) -> Dict[str, Any]:
        """Build a filter query for upsert operations."""
        # Try to use primary key if available
        if table_info.primary_key and table_info.primary_key in record:
            return {table_info.primary_key: record[table_info.primary_key]}
        
        # Fall back to using multiple fields
        filter_fields = ['id', 'name', 'email', 'sku', 'code']
        filter_query = {}
        
        for field in filter_fields:
            if field in record:
                filter_query[field] = record[field]
                break
        
        return filter_query or {'_id': record.get('_id')}
    
    async def pause_sync(self):
        """Pause the current sync operation."""
        if self.status == SyncStatus.RUNNING:
            self._stop_requested = True
            logger.info("Sync pause requested")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and metrics."""
        return {
            "status": self.status.value,
            "current_sync": {
                "sync_id": self.current_sync.sync_id if self.current_sync else None,
                "start_time": self.current_sync.start_time.isoformat() if self.current_sync else None,
                "tables_processed": len(self.current_sync.tables_synced) if self.current_sync else 0,
                "total_records": self.current_sync.total_records if self.current_sync else 0,
                "total_errors": self.current_sync.total_errors if self.current_sync else 0
            } if self.current_sync else None,
            "configuration": {
                "mysql_database": getattr(settings, 'MYSQL_DATABASE', None),
                "sync_enabled": getattr(settings, 'SYNC_ENABLED', False),
                "batch_size": getattr(settings, 'SYNC_BATCH_SIZE', 1000),
                "sync_tables": getattr(settings, 'SYNC_TABLES', None)
            }
        }
    
    async def test_connections(self) -> Dict[str, bool]:
        """Test MySQL and MongoDB connections."""
        results = {
            "mysql": False,
            "mongodb": False
        }
        
        try:
            if self.mysql_connector and self.mysql_connector.is_connected:
                results["mysql"] = True
        except Exception:
            pass
        
        try:
            if self.mongodb is not None:
                await self.mongodb.list_collection_names()
                results["mongodb"] = True
        except Exception:
            pass
        
        return results