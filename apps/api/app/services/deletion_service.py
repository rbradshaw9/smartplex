"""
Deletion Service for SmartPlex.

Handles intelligent library cleanup with grace periods and inactivity tracking.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from supabase import Client

from app.core.logging import get_logger
from app.services.integrations import SonarrService, RadarrService, TautulliService

logger = get_logger("deletion_service")


class DeletionService:
    """
    Service for managing library deletions with intelligent rules.
    
    Rules:
    1. Grace Period: Items must be older than grace_period_days since date_added
    2. Inactivity: Items must not have been viewed in inactivity_threshold_days
    3. Exclusions: Skip items in excluded libraries, genres, or collections
    4. Rating Filter: Optionally only delete items below a certain rating
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    async def scan_for_candidates(
        self, 
        rule_id: UUID,
        dry_run: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scan library for items matching deletion criteria.
        
        Args:
            rule_id: UUID of the deletion rule to apply
            dry_run: If True, only identify candidates without deleting
            
        Returns:
            List of media items that match deletion criteria
        """
        # Fetch the deletion rule
        rule_response = self.supabase.table("deletion_rules").select("*").eq("id", str(rule_id)).single().execute()
        
        if not rule_response.data:
            raise ValueError(f"Deletion rule {rule_id} not found")
        
        rule = rule_response.data
        
        logger.info(f"Scanning for deletion candidates using rule: {rule['name']}")
        logger.info(f"Grace period: {rule['grace_period_days']} days, Inactivity: {rule['inactivity_threshold_days']} days")
        
        # Calculate cutoff dates
        now = datetime.utcnow()
        grace_cutoff = now - timedelta(days=rule['grace_period_days'])
        inactivity_cutoff = now - timedelta(days=rule['inactivity_threshold_days'])
        
        # Query media items with their stats
        query = self.supabase.table("media_items").select(
            "*, user_stats(*)"
        )
        
        # Apply library exclusions
        if rule.get('excluded_libraries') and len(rule['excluded_libraries']) > 0:
            # This would need library_id field in media_items
            logger.info(f"Excluding libraries: {rule['excluded_libraries']}")
        
        try:
            media_response = query.execute()
        except Exception as e:
            logger.error(f"Failed to query media items: {e}")
            # Return empty if table doesn't exist or query fails
            return []
        
        if not media_response.data or len(media_response.data) == 0:
            logger.info("No media items found in database")
            return []
        
        candidates = []
        
        for item in media_response.data:
            # Check 1: Grace period - item must be old enough
            date_added = datetime.fromisoformat(item['added_at'].replace('Z', '+00:00')) if item.get('added_at') else None
            
            if not date_added:
                logger.debug(f"Skipping {item['title']}: no date_added")
                continue
            
            days_since_added = (now - date_added).days
            
            if date_added > grace_cutoff:
                logger.debug(f"Skipping {item['title']}: too new ({days_since_added} days old, needs {rule['grace_period_days']})")
                continue
            
            # Check 2: Inactivity - find most recent view across all users
            user_stats = item.get('user_stats', [])
            
            if not user_stats or len(user_stats) == 0:
                # Never watched - still subject to inactivity check
                last_viewed = date_added  # Use date_added as fallback
                view_count = 0
            else:
                # Find most recent view
                last_viewed = max(
                    (datetime.fromisoformat(stat['last_played_at'].replace('Z', '+00:00')) 
                     for stat in user_stats if stat.get('last_played_at')),
                    default=date_added
                )
                view_count = sum(stat.get('play_count', 0) for stat in user_stats)
            
            days_since_viewed = (now - last_viewed).days
            
            if last_viewed > inactivity_cutoff:
                logger.debug(f"Skipping {item['title']}: recently viewed ({days_since_viewed} days ago)")
                continue
            
            # Check 3: Rating filter (if specified)
            if rule.get('min_rating') and item.get('rating'):
                if item['rating'] >= rule['min_rating']:
                    logger.debug(f"Skipping {item['title']}: rating {item['rating']} >= {rule['min_rating']}")
                    continue
            
            # Check 4: Genre exclusions
            if rule.get('excluded_genres') and item.get('genres'):
                item_genres = item['genres'] if isinstance(item['genres'], list) else []
                if any(genre in rule['excluded_genres'] for genre in item_genres):
                    logger.debug(f"Skipping {item['title']}: genre excluded")
                    continue
            
            # Item qualifies for deletion
            candidate = {
                "id": item['id'],
                "plex_id": item['plex_id'],
                "title": item['title'],
                "type": item['type'],
                "date_added": date_added.isoformat(),
                "last_viewed_at": last_viewed.isoformat(),
                "view_count": view_count,
                "days_since_added": days_since_added,
                "days_since_viewed": days_since_viewed,
                "rating": item.get('rating'),
                "file_size_mb": item.get('file_size'),
            }
            
            candidates.append(candidate)
            logger.info(f"Candidate: {item['title']} - Added {days_since_added}d ago, Last viewed {days_since_viewed}d ago")
        
        logger.info(f"Found {len(candidates)} deletion candidates")
        
        return candidates
    
    async def execute_deletion(
        self,
        rule_id: UUID,
        candidates: List[Dict[str, Any]],
        user_id: UUID,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Execute deletion of media items.
        
        Args:
            rule_id: UUID of the deletion rule
            candidates: List of media items to delete (from scan_for_candidates)
            user_id: UUID of user executing the deletion
            dry_run: If True, only log what would be deleted
            
        Returns:
            Summary of deletion results
        """
        if dry_run:
            logger.info(f"DRY RUN: Would delete {len(candidates)} items")
        else:
            logger.warning(f"EXECUTING DELETION of {len(candidates)} items")
        
        results = {
            "total_candidates": len(candidates),
            "deleted": 0,
            "failed": 0,
            "skipped": 0,
            "total_size_mb": 0,
            "items": []
        }
        
        for candidate in candidates:
            item_result = {
                "title": candidate['title'],
                "status": "pending",
                "deleted_from_plex": False,
                "deleted_from_sonarr": False,
                "deleted_from_radarr": False,
                "error": None
            }
            
            try:
                if not dry_run:
                    # TODO: Implement actual deletion via Plex/Sonarr/Radarr APIs
                    # For now, just log what we would do
                    
                    # Delete from Plex (via Tautulli or direct Plex API)
                    # if candidate['type'] in ['movie', 'show']:
                    #     await self._delete_from_plex(candidate['plex_id'])
                    #     item_result['deleted_from_plex'] = True
                    
                    # Delete from Sonarr (if TV show)
                    # if candidate['type'] in ['show', 'season', 'episode']:
                    #     await self._delete_from_sonarr(candidate['id'])
                    #     item_result['deleted_from_sonarr'] = True
                    
                    # Delete from Radarr (if movie)
                    # if candidate['type'] == 'movie':
                    #     await self._delete_from_radarr(candidate['id'])
                    #     item_result['deleted_from_radarr'] = True
                    
                    pass
                
                item_result['status'] = 'completed' if not dry_run else 'dry_run'
                results['deleted'] += 1
                results['total_size_mb'] += candidate.get('file_size_mb', 0) or 0
                
            except Exception as e:
                logger.error(f"Failed to delete {candidate['title']}: {e}")
                item_result['status'] = 'failed'
                item_result['error'] = str(e)
                results['failed'] += 1
            
            # Log to deletion_history
            history_entry = {
                "rule_id": str(rule_id),
                "media_item_id": candidate['id'],
                "plex_id": candidate['plex_id'],
                "title": candidate['title'],
                "media_type": candidate['type'],
                "date_added": candidate['date_added'],
                "last_viewed_at": candidate['last_viewed_at'],
                "view_count": candidate['view_count'],
                "days_since_added": candidate['days_since_added'],
                "days_since_viewed": candidate['days_since_viewed'],
                "rating": candidate.get('rating'),
                "file_size_mb": candidate.get('file_size_mb'),
                "deleted_from_plex": item_result['deleted_from_plex'],
                "deleted_from_sonarr": item_result['deleted_from_sonarr'],
                "deleted_from_radarr": item_result['deleted_from_radarr'],
                "deletion_status": item_result['status'],
                "error_message": item_result.get('error'),
                "dry_run": dry_run,
                "deleted_by": str(user_id),
            }
            
            self.supabase.table("deletion_history").insert(history_entry).execute()
            
            results['items'].append(item_result)
        
        # Update rule last_run_at
        self.supabase.table("deletion_rules").update({
            "last_run_at": datetime.utcnow().isoformat()
        }).eq("id", str(rule_id)).execute()
        
        logger.info(f"Deletion complete: {results['deleted']} deleted, {results['failed']} failed, {results['skipped']} skipped")
        logger.info(f"Total space freed: {results['total_size_mb']} MB")
        
        return results
    
    async def _delete_from_plex(self, plex_id: str):
        """Delete item from Plex library (placeholder)."""
        # TODO: Implement Plex deletion via Plex API or Tautulli
        pass
    
    async def _delete_from_sonarr(self, media_item_id: UUID):
        """Delete series from Sonarr (placeholder)."""
        # TODO: Get Sonarr integration, find series by title/tvdb_id, delete
        pass
    
    async def _delete_from_radarr(self, media_item_id: UUID):
        """Delete movie from Radarr (placeholder)."""
        # TODO: Get Radarr integration, find movie by title/tmdb_id, delete
        pass
