"""
Sync control API endpoints.
Provides REST API for managing MySQL-MongoDB synchronization.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ...sync.sync_service import SyncService
from ...sync.scheduler import SyncScheduler
from ...config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])

# Global sync service and scheduler instances
_sync_service: Optional[SyncService] = None
_sync_scheduler: Optional[SyncScheduler] = None


async def get_sync_service() -> SyncService:
    """Dependency to get sync service instance."""
    global _sync_service
    if _sync_service is None:
        from ...database.mongodb import mongodb_client
        
        # Ensure MongoDB is connected
        if not mongodb_client.is_connected:
            try:
                await mongodb_client.connect()
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"MongoDB connection failed: {e}")
        
        _sync_service = SyncService()
        if not await _sync_service.initialize():
            raise HTTPException(status_code=503, detail="Sync service initialization failed")
    
    # Check if MySQL connection is still valid
    elif _sync_service.mysql_connector and not _sync_service.mysql_connector.is_connected:
        logger.warning("MySQL connection lost, reinitializing sync service")
        _sync_service = None  # Force re-initialization
        return await get_sync_service()  # Recursive call to reinitialize
        
    return _sync_service


async def get_sync_scheduler() -> SyncScheduler:
    """Dependency to get sync scheduler instance."""
    global _sync_scheduler, _sync_service
    if _sync_scheduler is None:
        if _sync_service is None:
            await get_sync_service()
        _sync_scheduler = SyncScheduler(_sync_service.sync_all_tables)
    return _sync_scheduler


class SyncTriggerRequest(BaseModel):
    """Request model for triggering sync."""
    tables: Optional[list[str]] = Field(None, description="Specific tables to sync (optional)")
    sync_all_tables: bool = Field(False, description="Sync all tables from source database")
    force_full_sync: bool = Field(False, description="Force full sync instead of incremental")


class SchedulerUpdateRequest(BaseModel):
    """Request model for updating scheduler settings."""
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Sync interval in minutes")
    enabled: Optional[bool] = Field(None, description="Enable/disable scheduler")


@router.get("/status")
async def get_sync_status(
    sync_service: SyncService = Depends(get_sync_service),
    scheduler: SyncScheduler = Depends(get_sync_scheduler)
):
    """Get current sync status and configuration."""
    try:
        service_status = await sync_service.get_sync_status()
        scheduler_status = scheduler.get_status()
        
        return {
            "sync_service": service_status,
            "scheduler": scheduler_status,
            "configuration": {
                "mysql_database": getattr(settings, 'MYSQL_DATABASE', None),
                "mysql_host": getattr(settings, 'MYSQL_HOST', None),
                "sync_enabled": getattr(settings, 'SYNC_ENABLED', False),
                "batch_size": getattr(settings, 'SYNC_BATCH_SIZE', 1000),
                "sync_tables": getattr(settings, 'SYNC_TABLES', None),
                "sync_only_timestamp_tables": getattr(settings, 'SYNC_ONLY_TIMESTAMP_TABLES', True)
            }
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-all")
async def sync_all_tables(
    force_full: bool = False,
    background_tasks: BackgroundTasks = None,
    sync_service: SyncService = Depends(get_sync_service)
):
    """Sync ALL tables from source database to MongoDB."""
    request = SyncTriggerRequest(
        sync_all_tables=True,
        force_full_sync=force_full
    )
    return await trigger_sync(request, background_tasks, sync_service)


@router.post("/trigger")
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    sync_service: SyncService = Depends(get_sync_service)
):
    """Trigger a manual sync operation."""
    try:
        if sync_service.status.value == "running":
            raise HTTPException(status_code=409, detail="Sync is already running")

        # Save original configuration
        original_tables = getattr(settings, 'SYNC_TABLES', None)
        original_timestamp_only = getattr(settings, 'SYNC_ONLY_TIMESTAMP_TABLES', True)

        # Configure tables to sync
        if request.sync_all_tables:
            # Sync all tables from database
            settings.SYNC_TABLES = None
            settings.SYNC_ONLY_TIMESTAMP_TABLES = False
        elif request.tables:
            # Sync specific tables
            settings.SYNC_TABLES = ','.join(request.tables)

        # Reset sync times for force full sync
        if request.force_full_sync:
            if request.tables:
                for table in request.tables:
                    await sync_service.sync_tracker.reset_sync_time(table)
            else:
                await sync_service.sync_tracker.reset_all_sync_times()

        # Start sync in background
        background_tasks.add_task(sync_service.sync_all_tables)

        # Restore original configuration after task is added
        if request.sync_all_tables or request.tables:
            settings.SYNC_TABLES = original_tables
            settings.SYNC_ONLY_TIMESTAMP_TABLES = original_timestamp_only

        # Determine what's being synced
        if request.sync_all_tables:
            sync_target = "all tables from source database"
        elif request.tables:
            sync_target = f"tables: {', '.join(request.tables)}"
        else:
            sync_target = "configured tables"

        return {
            "message": "Sync triggered successfully",
            "tables": sync_target,
            "force_full_sync": request.force_full_sync
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_sync(sync_service: SyncService = Depends(get_sync_service)):
    """Pause the current sync operation."""
    try:
        await sync_service.pause_sync()
        return {"message": "Sync pause requested"}
    except Exception as e:
        logger.error(f"Error pausing sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def discover_tables(sync_service: SyncService = Depends(get_sync_service)):
    """Discover all available tables in the MySQL database."""
    try:
        if not sync_service.mysql_connector:
            raise HTTPException(status_code=503, detail="MySQL connector not initialized")
        
        all_tables = await sync_service.mysql_connector.discover_all_tables()
        sync_ready_tables = await sync_service.mysql_connector.get_tables_with_timestamps()
        
        tables_info = []
        for table_name, table_info in all_tables.items():
            is_sync_ready = table_name in sync_ready_tables
            
            tables_info.append({
                "table_name": table_name,
                "primary_key": table_info.primary_key,
                "has_created_at": table_info.has_created_at,
                "has_updated_at": table_info.has_updated_at,
                "created_at_column": table_info.created_at_column,
                "updated_at_column": table_info.updated_at_column,
                "sync_ready": is_sync_ready,
                "column_count": len(table_info.columns),
                "columns": list(table_info.columns.keys())
            })
        
        return {
            "total_tables": len(all_tables),
            "sync_ready_tables": len(sync_ready_tables),
            "tables": tables_info
        }
        
    except Exception as e:
        logger.error(f"Error discovering tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/sample")
async def get_table_sample(
    table_name: str,
    limit: int = 5,
    sync_service: SyncService = Depends(get_sync_service)
):
    """Get sample data from a specific table."""
    try:
        if not sync_service.mysql_connector:
            raise HTTPException(status_code=503, detail="MySQL connector not initialized")
        
        # Check if table exists
        all_tables = await sync_service.mysql_connector.discover_all_tables()
        if table_name not in all_tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        sample_data = await sync_service.mysql_connector.get_sample_data(table_name, limit)
        table_count = await sync_service.mysql_connector.get_table_count(table_name)
        
        return {
            "table_name": table_name,
            "total_records": table_count,
            "sample_size": len(sample_data),
            "sample_data": [dict(record) for record in sample_data]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_sync_history(sync_service: SyncService = Depends(get_sync_service)):
    """Get sync history and statistics."""
    try:
        sync_stats = await sync_service.sync_tracker.get_sync_statistics()
        return {
            "sync_statistics": sync_stats,
            "current_sync": {
                "sync_id": sync_service.current_sync.sync_id if sync_service.current_sync else None,
                "status": sync_service.status.value,
                "start_time": sync_service.current_sync.start_time.isoformat() if sync_service.current_sync else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/start")
async def start_scheduler(scheduler: SyncScheduler = Depends(get_sync_scheduler)):
    """Start the sync scheduler."""
    try:
        await scheduler.start()
        return {"message": "Scheduler started", "status": scheduler.get_status()}
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_scheduler(scheduler: SyncScheduler = Depends(get_sync_scheduler)):
    """Stop the sync scheduler."""
    try:
        await scheduler.stop()
        return {"message": "Scheduler stopped"}
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/pause")
async def pause_scheduler(scheduler: SyncScheduler = Depends(get_sync_scheduler)):
    """Pause the sync scheduler."""
    try:
        await scheduler.pause()
        return {"message": "Scheduler paused", "status": scheduler.get_status()}
    except Exception as e:
        logger.error(f"Error pausing scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/resume")
async def resume_scheduler(scheduler: SyncScheduler = Depends(get_sync_scheduler)):
    """Resume the sync scheduler."""
    try:
        await scheduler.resume()
        return {"message": "Scheduler resumed", "status": scheduler.get_status()}
    except Exception as e:
        logger.error(f"Error resuming scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduler")
async def update_scheduler(
    request: SchedulerUpdateRequest,
    scheduler: SyncScheduler = Depends(get_sync_scheduler)
):
    """Update scheduler configuration."""
    try:
        updated_fields = []
        
        if request.interval_minutes is not None:
            await scheduler.update_interval(request.interval_minutes)
            updated_fields.append(f"interval: {request.interval_minutes} minutes")
        
        if request.enabled is not None:
            if request.enabled and scheduler.is_stopped():
                await scheduler.start()
                updated_fields.append("enabled: true")
            elif not request.enabled and not scheduler.is_stopped():
                await scheduler.stop()
                updated_fields.append("enabled: false")
        
        return {
            "message": f"Scheduler updated: {', '.join(updated_fields)}" if updated_fields else "No changes made",
            "status": scheduler.get_status()
        }
        
    except Exception as e:
        logger.error(f"Error updating scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status(scheduler: SyncScheduler = Depends(get_sync_scheduler)):
    """Get scheduler status and timing information."""
    return scheduler.get_status()


@router.post("/reset/{table_name}")
async def reset_table_sync(
    table_name: str,
    sync_service: SyncService = Depends(get_sync_service)
):
    """Reset sync timestamp for a specific table (forces full sync on next run)."""
    try:
        await sync_service.sync_tracker.reset_sync_time(table_name)
        return {"message": f"Sync timestamp reset for table: {table_name}"}
    except Exception as e:
        logger.error(f"Error resetting table sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-all")
async def reset_all_sync(sync_service: SyncService = Depends(get_sync_service)):
    """Reset all sync timestamps (forces full sync for all tables on next run)."""
    try:
        await sync_service.sync_tracker.reset_all_sync_times()
        return {"message": "All sync timestamps reset"}
    except Exception as e:
        logger.error(f"Error resetting all sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_sync_health(sync_service: SyncService = Depends(get_sync_service)):
    """Get health status of sync connections."""
    try:
        connection_status = await sync_service.test_connections()
        
        return {
            "mysql_connection": "healthy" if connection_status["mysql"] else "unhealthy",
            "mongodb_connection": "healthy" if connection_status["mongodb"] else "unhealthy",
            "sync_service_status": sync_service.status.value,
            "last_sync": sync_service.current_sync.start_time.isoformat() if sync_service.current_sync else None,
            "overall_health": "healthy" if all(connection_status.values()) else "unhealthy"
        }
    except Exception as e:
        logger.error(f"Error checking sync health: {e}")
        raise HTTPException(status_code=500, detail=str(e))