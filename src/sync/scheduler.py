"""
Dynamic sync scheduler with configurable intervals.
Handles background sync operations with runtime control.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum

from ..config.settings import settings

logger = logging.getLogger(__name__)


class SchedulerStatus(Enum):
    """Scheduler status enum."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SyncScheduler:
    """
    Background scheduler for automated sync operations.
    Supports dynamic interval changes and runtime control.
    """
    
    def __init__(self, sync_function: Callable[[], Awaitable]):
        """
        Initialize scheduler with sync function.
        
        Args:
            sync_function: Async function to call for sync operations
        """
        self.sync_function = sync_function
        self.status = SchedulerStatus.STOPPED
        self.interval_minutes = getattr(settings, 'SYNC_INTERVAL_MINUTES', 60)
        self.last_sync_time: Optional[datetime] = None
        self.next_sync_time: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._interval_changed = asyncio.Event()
    
    async def start(self):
        """Start the scheduler."""
        if self.status == SchedulerStatus.RUNNING:
            logger.warning("Scheduler is already running")
            return
        
        if not getattr(settings, 'SYNC_ENABLED', False):
            logger.warning("Sync is disabled in configuration")
            return
        
        self.status = SchedulerStatus.RUNNING
        self._stop_event.clear()
        self._pause_event.set()  # Start unpaused
        
        # Start the background task
        self._task = asyncio.create_task(self._scheduler_loop())
        
        logger.info(f"Sync scheduler started with {self.interval_minutes}-minute intervals")
    
    async def stop(self):
        """Stop the scheduler."""
        if self.status == SchedulerStatus.STOPPED:
            return
        
        self.status = SchedulerStatus.STOPPED
        self._stop_event.set()
        
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Scheduler task did not stop gracefully, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        self._task = None
        self.next_sync_time = None
        
        logger.info("Sync scheduler stopped")
    
    async def pause(self):
        """Pause the scheduler without stopping it."""
        if self.status == SchedulerStatus.RUNNING:
            self.status = SchedulerStatus.PAUSED
            self._pause_event.clear()
            logger.info("Sync scheduler paused")
    
    async def resume(self):
        """Resume the scheduler if paused."""
        if self.status == SchedulerStatus.PAUSED:
            self.status = SchedulerStatus.RUNNING
            self._pause_event.set()
            logger.info("Sync scheduler resumed")
    
    async def update_interval(self, minutes: int):
        """
        Update sync interval dynamically.
        
        Args:
            minutes: New interval in minutes
        """
        if minutes < 1:
            raise ValueError("Interval must be at least 1 minute")
        
        old_interval = self.interval_minutes
        self.interval_minutes = minutes
        
        # Signal that interval changed
        self._interval_changed.set()
        
        # Update next sync time
        if self.last_sync_time:
            self.next_sync_time = self.last_sync_time + timedelta(minutes=minutes)
        else:
            self.next_sync_time = datetime.now() + timedelta(minutes=minutes)
        
        logger.info(f"Sync interval updated from {old_interval} to {minutes} minutes")
    
    async def trigger_immediate_sync(self):
        """Trigger an immediate sync operation."""
        if self.status == SchedulerStatus.STOPPED:
            logger.warning("Cannot trigger sync: scheduler is stopped")
            return False
        
        try:
            logger.info("Triggering immediate sync")
            await self._execute_sync()
            return True
        except Exception as e:
            logger.error(f"Immediate sync failed: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get current scheduler status and timing information."""
        return {
            "status": self.status.value,
            "interval_minutes": self.interval_minutes,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "next_sync_time": self.next_sync_time.isoformat() if self.next_sync_time else None,
            "sync_enabled": getattr(settings, 'SYNC_ENABLED', False),
            "time_until_next_sync": self._get_time_until_next_sync()
        }
    
    def _get_time_until_next_sync(self) -> Optional[str]:
        """Get human-readable time until next sync."""
        if not self.next_sync_time or self.status != SchedulerStatus.RUNNING:
            return None
        
        time_diff = self.next_sync_time - datetime.now()
        if time_diff.total_seconds() <= 0:
            return "Due now"
        
        total_seconds = int(time_diff.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        # Calculate initial next sync time
        self.next_sync_time = datetime.now() + timedelta(minutes=self.interval_minutes)
        
        try:
            while not self._stop_event.is_set():
                # Wait for pause to be cleared (resume)
                await self._pause_event.wait()
                
                # Check if we should stop
                if self._stop_event.is_set():
                    break
                
                # Calculate time to wait until next sync
                now = datetime.now()
                if self.next_sync_time and now >= self.next_sync_time:
                    # Time for sync
                    await self._execute_sync()
                    
                    # Schedule next sync
                    self.next_sync_time = datetime.now() + timedelta(minutes=self.interval_minutes)
                
                # Wait for either:
                # 1. Time for next sync (max 60 seconds)
                # 2. Stop signal
                # 3. Pause signal
                # 4. Interval change signal
                wait_time = min(60, max(1, (self.next_sync_time - datetime.now()).total_seconds()))
                
                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            self._stop_event.wait(),
                            self._interval_changed.wait(),
                            return_when=asyncio.FIRST_COMPLETED
                        ),
                        timeout=wait_time
                    )
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    pass
                
                # Clear interval changed event
                if self._interval_changed.is_set():
                    self._interval_changed.clear()
        
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            self.status = SchedulerStatus.STOPPED
        
        logger.info("Scheduler loop ended")
    
    async def _execute_sync(self):
        """Execute a sync operation."""
        try:
            logger.info("Executing scheduled sync")
            sync_start_time = datetime.now()
            
            # Execute the sync function
            await self.sync_function()
            
            # Update timing
            self.last_sync_time = sync_start_time
            sync_duration = (datetime.now() - sync_start_time).total_seconds()
            
            logger.info(f"Scheduled sync completed in {sync_duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}")
            # Don't stop the scheduler on sync failure
            # Just log and continue with next scheduled sync
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.status == SchedulerStatus.RUNNING
    
    def is_paused(self) -> bool:
        """Check if scheduler is paused."""
        return self.status == SchedulerStatus.PAUSED
    
    def is_stopped(self) -> bool:
        """Check if scheduler is stopped."""
        return self.status == SchedulerStatus.STOPPED