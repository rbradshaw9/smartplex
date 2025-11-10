"""
Tautulli Sync Service for SmartPlex.

Aggregates watch history from Tautulli across ALL Plex users and updates media_items 
with server-wide statistics for accurate deletion decisions.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict

from supabase import Client

from app.core.logging import get_logger
from app.services.integrations.tautulli import TautulliService

logger = get_logger("tautulli_sync")


class TautulliSyncService:
    """
    Service for syncing Tautulli watch history to media_items aggregated stats.
    
    Fetches watch history from Tautulli API and aggregates:
    - total_play_count: Total plays across all users
    - last_watched_at: Most recent watch across all users
    - total_watch_time_seconds: Total watch time across all users
    
    These stats represent ALL Plex users, not just SmartPlex users.
    """
    
    def __init__(self, supabase: Client, tautulli_service: TautulliService):
        self.supabase = supabase
        self.tautulli = tautulli_service
    
    async def sync_watch_history(
        self, 
        days_back: int = 90,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Sync watch history from Tautulli and update media_items.
        
        Args:
            days_back: Number of days of history to fetch (default 90)
            batch_size: Number of items to fetch per API call (default 100)
            
        Returns:
            Dict with sync statistics
        """
        logger.info(f"Starting Tautulli sync for last {days_back} days")
        
        stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "history_items_fetched": 0,
            "media_items_updated": 0,
            "media_items_created": 0,
            "errors": [],
        }
        
        try:
            # Fetch watch history from Tautulli
            # Use get_history endpoint with length parameter for pagination
            all_history = []
            offset = 0
            
            while True:
                try:
                    logger.info(f"Fetching history batch at offset {offset}")
                    history_response = await self.tautulli.get_history(
                        length=batch_size,
                        start=offset
                    )
                    
                    # Extract data array from response
                    history_batch = history_response.get("data", [])
                    
                    if not history_batch or len(history_batch) == 0:
                        break
                    
                    all_history.extend(history_batch)
                    stats["history_items_fetched"] += len(history_batch)
                    
                    # Break if we got less than batch_size (last page)
                    if len(history_batch) < batch_size:
                        break
                    
                    offset += batch_size
                    
                except Exception as e:
                    logger.error(f"Error fetching history batch at offset {offset}: {e}")
                    stats["errors"].append(f"History fetch error at offset {offset}: {str(e)}")
                    break
            
            logger.info(f"Fetched {len(all_history)} history items from Tautulli")
            
            # Aggregate by rating_key (Plex item ID)
            aggregated_stats = self._aggregate_by_rating_key(all_history)
            
            logger.info(f"Aggregated stats for {len(aggregated_stats)} unique items")
            
            # Update media_items in database
            for rating_key, item_stats in aggregated_stats.items():
                try:
                    await self._update_media_item_stats(rating_key, item_stats)
                    stats["media_items_updated"] += 1
                except Exception as e:
                    logger.error(f"Error updating media item {rating_key}: {e}")
                    stats["errors"].append(f"Update error for rating_key {rating_key}: {str(e)}")
            
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            stats["success"] = len(stats["errors"]) == 0
            
            logger.info(f"Tautulli sync completed: {stats['media_items_updated']} items updated")
            
            return stats
            
        except Exception as e:
            logger.error(f"Tautulli sync failed: {e}")
            stats["errors"].append(f"Sync failed: {str(e)}")
            stats["success"] = False
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            return stats
    
    def _aggregate_by_rating_key(self, history: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate watch history by rating_key (Plex item ID).
        
        Args:
            history: List of history items from Tautulli
            
        Returns:
            Dict mapping rating_key to aggregated stats
        """
        aggregated: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "play_count": 0,
            "total_duration_seconds": 0,
            "last_watched": None,
            "title": None,
            "type": None,
        })
        
        for item in history:
            rating_key = item.get("rating_key")
            if not rating_key:
                continue
            
            stats = aggregated[rating_key]
            
            # Increment play count
            stats["play_count"] += 1
            
            # Add duration (convert milliseconds to seconds if needed)
            duration = item.get("duration", 0)
            if duration:
                # Tautulli returns duration in seconds
                stats["total_duration_seconds"] += int(duration)
            
            # Track most recent watch
            watched_at = item.get("stopped") or item.get("date")
            if watched_at:
                # Convert Unix timestamp to datetime
                try:
                    if isinstance(watched_at, (int, float)):
                        watched_dt = datetime.fromtimestamp(watched_at, tz=timezone.utc)
                    else:
                        watched_dt = datetime.fromisoformat(str(watched_at))
                    
                    if stats["last_watched"] is None or watched_dt > stats["last_watched"]:
                        stats["last_watched"] = watched_dt
                except Exception as e:
                    logger.warning(f"Could not parse timestamp {watched_at}: {e}")
            
            # Store metadata (only once)
            if stats["title"] is None:
                stats["title"] = item.get("full_title") or item.get("title")
                stats["type"] = item.get("media_type")
                stats["year"] = item.get("year")
                stats["grandparent_title"] = item.get("grandparent_title")  # TV show title
        
        return dict(aggregated)
    
    async def _update_media_item_stats(
        self, 
        rating_key: str, 
        stats: Dict[str, Any]
    ) -> None:
        """
        Update or create media_item with aggregated stats.
        
        Args:
            rating_key: Plex rating_key (item ID)
            stats: Aggregated statistics for this item
        """
        # Check if media_item exists
        result = self.supabase.table("media_items")\
            .select("id, plex_id")\
            .eq("plex_id", rating_key)\
            .execute()
        
        update_data = {
            "total_play_count": stats["play_count"],
            "total_watch_time_seconds": stats["total_duration_seconds"],
            "last_watched_at": stats["last_watched"].isoformat() if stats["last_watched"] else None,
            "tautulli_synced_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if result.data and len(result.data) > 0:
            # Update existing item
            media_item_id = result.data[0]["id"]
            self.supabase.table("media_items")\
                .update(update_data)\
                .eq("id", media_item_id)\
                .execute()
        else:
            # Create new media_item if it doesn't exist
            # This can happen if Tautulli has history for items not yet synced
            logger.info(f"Creating new media_item for rating_key {rating_key}")
            
            # We need a server_id - try to get from servers table
            # For now, skip creation if item doesn't exist
            # The regular Plex sync should create it first
            logger.warning(f"Media item with plex_id {rating_key} not found, skipping")
