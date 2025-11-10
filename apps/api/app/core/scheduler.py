"""
Background scheduler for SmartPlex API.

Handles periodic sync tasks:
- Plex library sync
- Tautulli watch history aggregation
- Integration health checks
"""

from datetime import datetime, timezone
from typing import Optional
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from supabase import Client

from app.config import Settings
from app.services.tautulli_sync import TautulliSyncService
from app.services.integrations.tautulli import TautulliService

logger = logging.getLogger("scheduler")


class BackgroundScheduler:
    """Manages background sync and maintenance tasks."""
    
    def __init__(self, supabase: Client, settings: Settings):
        self.supabase = supabase
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        
    async def start(self):
        """Start the background scheduler."""
        logger.info("🚀 Starting background scheduler...")
        
        # Get sync intervals from settings table
        sync_intervals = await self._get_sync_intervals()
        
        # Schedule Tautulli sync (every N hours)
        tautulli_hours = sync_intervals.get("tautulli_sync_hours", 6)
        if tautulli_hours > 0:
            self.scheduler.add_job(
                self._sync_tautulli,
                IntervalTrigger(hours=tautulli_hours),
                id="tautulli_sync",
                name="Tautulli Watch History Sync",
                replace_existing=True,
            )
            logger.info(f"📅 Scheduled Tautulli sync every {tautulli_hours} hours")
        
        # Schedule Plex library sync (every N hours)
        plex_hours = sync_intervals.get("plex_sync_hours", 12)
        if plex_hours > 0:
            self.scheduler.add_job(
                self._sync_plex_libraries,
                IntervalTrigger(hours=plex_hours),
                id="plex_library_sync",
                name="Plex Library Sync",
                replace_existing=True,
            )
            logger.info(f"📅 Scheduled Plex library sync every {plex_hours} hours")
        
        # Schedule integration health checks (every 30 minutes)
        self.scheduler.add_job(
            self._check_integration_health,
            IntervalTrigger(minutes=30),
            id="integration_health_check",
            name="Integration Health Check",
            replace_existing=True,
        )
        logger.info("📅 Scheduled integration health checks every 30 minutes")
        
        # Start the scheduler
        self.scheduler.start()
        logger.info(f"✅ Background scheduler started with {len(self.scheduler.get_jobs())} jobs")
    
    async def stop(self):
        """Stop the background scheduler."""
        logger.info("🛑 Stopping background scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("✅ Background scheduler stopped")
    
    async def _get_sync_intervals(self) -> dict:
        """Get sync interval settings from database."""
        try:
            # Get sync interval settings
            result = self.supabase.table("settings")\
                .select("key, value")\
                .in_("key", [
                    "tautulli_sync_hours",
                    "plex_sync_hours",
                    "integration_health_check_minutes"
                ])\
                .execute()
            
            intervals = {}
            if result.data:
                for setting in result.data:
                    try:
                        intervals[setting["key"]] = int(setting["value"])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid interval value for {setting['key']}: {setting['value']}")
            
            return intervals
            
        except Exception as e:
            logger.error(f"Failed to load sync intervals: {e}")
            return {}
    
    async def _sync_tautulli(self):
        """Background job to sync Tautulli watch history."""
        try:
            logger.info("🔄 Starting scheduled Tautulli sync...")
            
            # Get active Tautulli integration
            integration_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("service", "tautulli")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            
            if not integration_result.data or len(integration_result.data) == 0:
                logger.warning("⚠️ No active Tautulli integration found, skipping sync")
                return
            
            integration = integration_result.data[0]
            
            # Initialize services
            tautulli = TautulliService(
                url=integration["url"],
                api_key=integration["api_key"]
            )
            sync_service = TautulliSyncService(self.supabase, tautulli)
            
            # Run sync
            stats = await sync_service.sync_watch_history(days_back=90, batch_size=100)
            
            # Log result
            if stats["success"]:
                logger.info(
                    f"✅ Tautulli sync completed: "
                    f"{stats['history_items_fetched']} items fetched, "
                    f"{stats['media_items_updated']} updated"
                )
            else:
                logger.error(f"❌ Tautulli sync failed: {stats.get('errors', [])}")
            
            # Store sync record
            sync_record = {
                "user_id": integration["user_id"],
                "sync_type": "tautulli_scheduled",
                "status": "completed" if stats["success"] else "failed",
                "items_processed": stats["history_items_fetched"],
                "items_updated": stats["media_items_updated"],
                "items_added": 0,
                "items_removed": 0,
                "started_at": stats["started_at"],
                "completed_at": stats["completed_at"],
                "metadata": {
                    "scheduled": True,
                    "errors": stats["errors"]
                }
            }
            self.supabase.table("sync_history").insert(sync_record).execute()
            
        except Exception as e:
            logger.error(f"❌ Scheduled Tautulli sync failed: {e}")
    
    async def _sync_plex_libraries(self):
        """Background job to sync Plex library metadata."""
        try:
            logger.info("🔄 Starting scheduled Plex library sync...")
            
            # TODO: Implement full Plex library sync
            # This should:
            # 1. Get all active Plex servers
            # 2. For each server, fetch library sections
            # 3. For each item, extract metadata including:
            #    - plex_id (rating_key)
            #    - tmdb_id, tvdb_id, imdb_id (from guids)
            #    - title, year, type, file_path, file_size
            # 4. Upsert to media_items table
            # 5. Match with Sonarr/Radarr using tmdb_id/tvdb_id
            
            logger.info("⚠️ Plex library sync not yet implemented (placeholder)")
            
        except Exception as e:
            logger.error(f"❌ Scheduled Plex library sync failed: {e}")
    
    async def _check_integration_health(self):
        """Background job to check integration health."""
        try:
            logger.info("🏥 Checking integration health...")
            
            # Get all active integrations
            integrations_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("status", "active")\
                .execute()
            
            if not integrations_result.data:
                logger.info("No active integrations to check")
                return
            
            # Check each integration
            for integration in integrations_result.data:
                try:
                    # TODO: Add health check methods to each integration service
                    # For now, just log
                    logger.info(f"✅ {integration['service']}: {integration['name']}")
                except Exception as e:
                    logger.error(f"❌ Health check failed for {integration['name']}: {e}")
                    
                    # Update integration status to 'error'
                    self.supabase.table("integrations")\
                        .update({"status": "error"})\
                        .eq("id", integration["id"])\
                        .execute()
            
        except Exception as e:
            logger.error(f"❌ Integration health check failed: {e}")
    
    def get_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in self.scheduler.get_jobs()
        ]
    
    async def update_job_schedule(self, job_id: str, hours: int):
        """Update the schedule for a specific job."""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Reschedule with new interval
            self.scheduler.reschedule_job(
                job_id,
                trigger=IntervalTrigger(hours=hours)
            )
            logger.info(f"✅ Updated {job_id} to run every {hours} hours")
            
        except Exception as e:
            logger.error(f"❌ Failed to update job schedule: {e}")
            raise


# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


async def start_scheduler(supabase: Client, settings: Settings):
    """Start the global background scheduler."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler(supabase, settings)
        await _scheduler.start()
    
    return _scheduler


async def stop_scheduler():
    """Stop the global background scheduler."""
    global _scheduler
    
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Get the global scheduler instance."""
    return _scheduler
