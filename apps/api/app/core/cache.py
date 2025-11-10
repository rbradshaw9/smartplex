"""
Caching service for Plex data using Supabase as storage backend.
Implements smart caching with TTL and incremental sync support.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class PlexCache:
    """
    Caching layer for Plex data stored in Supabase.
    Reduces API calls by storing watch history, ratings, and sync metadata.
    """
    
    # Cache TTL (Time To Live) configurations
    WATCH_HISTORY_TTL = timedelta(minutes=15)  # Refresh every 15 minutes
    FULL_SYNC_TTL = timedelta(hours=6)  # Full library sync every 6 hours
    
    def __init__(self, supabase: Client, user_id: str):
        self.supabase = supabase
        self.user_id = user_id
    
    async def should_refresh_cache(self, cache_type: str = "watch_history") -> bool:
        """
        Check if cache needs refresh based on last sync time.
        
        Args:
            cache_type: Type of cache to check ('watch_history', 'full_sync')
            
        Returns:
            True if cache should be refreshed, False if still valid
        """
        try:
            # Get last sync record
            result = self.supabase.table('sync_history')\
                .select('completed_at, metadata')\
                .eq('user_id', self.user_id)\
                .eq('sync_type', cache_type)\
                .eq('status', 'completed')\
                .order('completed_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not result.data:
                # No sync found, need refresh
                return True
            
            last_sync = result.data[0]
            completed_at = datetime.fromisoformat(last_sync['completed_at'].replace('Z', '+00:00'))
            
            # Check TTL based on cache type
            ttl = self.WATCH_HISTORY_TTL if cache_type == "watch_history" else self.FULL_SYNC_TTL
            
            is_stale = datetime.now(completed_at.tzinfo) - completed_at > ttl
            
            if is_stale:
                logger.info(f"Cache for {cache_type} is stale (last sync: {completed_at})")
            
            return is_stale
            
        except Exception as e:
            logger.error(f"Error checking cache freshness: {e}")
            # On error, assume we need refresh
            return True
    
    async def get_cached_watch_history(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached watch history from database.
        
        Returns:
            Cached data if fresh, None if needs refresh
        """
        try:
            # Check if cache is still valid
            if await self.should_refresh_cache("watch_history"):
                return None
            
            # Get watch history from user_stats joined with media_items
            result = self.supabase.table('user_stats')\
                .select('*, media_items(*)')\
                .eq('user_id', self.user_id)\
                .order('last_played_at', desc=True)\
                .limit(50)\
                .execute()
            
            if not result.data:
                return None
            
            # Transform to expected format
            watch_history = []
            total_watched = 0
            total_hours = 0
            
            for stat in result.data:
                media = stat['media_items']
                if not media:
                    continue
                
                total_watched += stat['play_count']
                total_hours += (stat['total_duration_ms'] / 1000 / 60 / 60)
                
                watch_history.append({
                    "title": media['title'],
                    "type": media['type'],
                    "year": media['year'],
                    "duration": media['duration_ms'],
                    "last_viewed_at": stat['last_played_at'],
                    "view_count": stat['play_count'],
                    "user_rating": stat['rating'],
                    "completion_percentage": stat['completion_percentage'],
                    "metadata": media['metadata']
                })
            
            return {
                "watch_history": watch_history,
                "stats": {
                    "total_watched": total_watched,
                    "total_hours": round(total_hours, 1),
                    "cached": True,
                    "last_sync": result.data[0]['updated_at'] if result.data else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving cached watch history: {e}")
            return None
    
    async def cache_watch_history(
        self, 
        watch_data: Dict[str, Any],
        server_id: str
    ) -> bool:
        """
        Store watch history in database for caching.
        Upserts media_items and user_stats tables.
        
        Args:
            watch_data: Watch history data from Plex API
            server_id: UUID of the Plex server
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sync_started = datetime.utcnow()
            items_added = 0
            items_updated = 0
            
            # Process watch history items
            for item in watch_data.get("watch_history", []):
                try:
                    # Generate a stable plex_id from title and year
                    plex_id = f"{item['title']}_{item.get('year', 'unknown')}"
                    
                    # Upsert media item
                    media_result = self.supabase.table('media_items')\
                        .upsert({
                            'server_id': server_id,
                            'plex_id': plex_id,
                            'type': item['type'],
                            'title': item['title'],
                            'year': item.get('year'),
                            'duration_ms': item.get('duration'),
                            'file_size_bytes': item.get('file_size_bytes'),  # Store file size
                            'metadata': {
                                'thumb': item.get('thumb'),
                                'summary': item.get('summary'),
                                'genres': item.get('genres', []),
                                'rating': item.get('rating'),
                                'content_rating': item.get('content_rating'),
                                'plex_added_at': item.get('plex_added_at'),  # Store Plex addedAt timestamp
                            }
                        }, on_conflict='server_id,plex_id')\
                        .execute()
                    
                    if not media_result.data:
                        continue
                    
                    media_item_id = media_result.data[0]['id']
                    
                    # Upsert user stats
                    stats_result = self.supabase.table('user_stats')\
                        .upsert({
                            'user_id': self.user_id,
                            'media_item_id': media_item_id,
                            'play_count': item.get('view_count', 1),
                            'total_duration_ms': item.get('duration', 0) * item.get('view_count', 1),
                            'last_played_at': item.get('last_viewed_at'),
                            'rating': item.get('user_rating'),
                        }, on_conflict='user_id,media_item_id')\
                        .execute()
                    
                    if stats_result.data:
                        items_updated += 1
                    else:
                        items_added += 1
                        
                except Exception as item_error:
                    logger.error(f"Error caching item {item.get('title')}: {item_error}")
                    continue
            
            # Record sync completion
            self.supabase.table('sync_history').insert({
                'user_id': self.user_id,
                'server_id': server_id,
                'sync_type': 'watch_history',
                'status': 'completed',
                'items_processed': len(watch_data.get("watch_history", [])),
                'items_added': items_added,
                'items_updated': items_updated,
                'started_at': sync_started.isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
                'metadata': {
                    'stats': watch_data.get('stats', {}),
                    'cache_ttl_minutes': int(self.WATCH_HISTORY_TTL.total_seconds() / 60)
                }
            }).execute()
            
            logger.info(f"Cached {items_added + items_updated} watch history items for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching watch history: {e}")
            
            # Record failed sync
            try:
                self.supabase.table('sync_history').insert({
                    'user_id': self.user_id,
                    'server_id': server_id,
                    'sync_type': 'watch_history',
                    'status': 'failed',
                    'error_message': str(e),
                    'started_at': sync_started.isoformat(),
                }).execute()
            except:
                pass
            
            return False
    
    async def get_last_sync_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the last successful sync.
        
        Returns:
            Dict with sync timestamp and stats, or None
        """
        try:
            result = self.supabase.table('sync_history')\
                .select('*')\
                .eq('user_id', self.user_id)\
                .eq('status', 'completed')\
                .order('completed_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not result.data:
                return None
            
            sync = result.data[0]
            return {
                "last_sync_at": sync['completed_at'],
                "sync_type": sync['sync_type'],
                "items_processed": sync['items_processed'],
                "items_added": sync['items_added'],
                "items_updated": sync['items_updated'],
                "duration_seconds": (
                    datetime.fromisoformat(sync['completed_at'].replace('Z', '+00:00')) -
                    datetime.fromisoformat(sync['started_at'].replace('Z', '+00:00'))
                ).total_seconds() if sync.get('started_at') else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting last sync info: {e}")
            return None
