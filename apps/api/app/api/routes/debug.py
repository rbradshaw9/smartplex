"""
Debug endpoints for troubleshooting SmartPlex issues.

Admin-only endpoints to inspect system state and diagnose problems.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.supabase import get_supabase_client, require_admin
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("debug")


@router.get("/deletion-candidates-debug")
async def debug_deletion_candidates(
    grace_days: int = 30,
    inactivity_days: int = 90,
    limit: int = 10,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Debug endpoint to see why items are or aren't qualifying as deletion candidates.
    
    Shows the first N items and their status vs deletion criteria.
    """
    try:
        now = datetime.now(timezone.utc)
        grace_cutoff = now - timedelta(days=grace_days)
        inactivity_cutoff = now - timedelta(days=inactivity_days)
        
        # Get sample of media items
        media_response = supabase.table('media_items')\
            .select('*')\
            .limit(limit)\
            .execute()
        
        if not media_response.data:
            return {
                "message": "No media items in database",
                "total_items": 0,
                "items": []
            }
        
        results = []
        
        for item in media_response.data:
            # Get date_added
            metadata = item.get('metadata', {})
            plex_added_at = metadata.get('plex_added_at') if isinstance(metadata, dict) else None
            
            date_added = None
            date_added_source = None
            
            if plex_added_at:
                if 'Z' not in plex_added_at and '+' not in plex_added_at:
                    plex_added_at += '+00:00'
                date_added = datetime.fromisoformat(plex_added_at.replace('Z', '+00:00'))
                date_added_source = "plex_metadata"
            elif item.get('added_at'):
                date_added = datetime.fromisoformat(item['added_at'].replace('Z', '+00:00'))
                date_added_source = "database"
            
            # Get last_watched
            tautulli_last_watched = item.get('last_watched_at')
            last_viewed = None
            last_viewed_source = None
            view_count = item.get('total_play_count', 0)
            
            if tautulli_last_watched:
                last_viewed = datetime.fromisoformat(tautulli_last_watched.replace('Z', '+00:00'))
                last_viewed_source = "tautulli"
            elif date_added:
                last_viewed = date_added
                last_viewed_source = "fallback_to_added"
            
            # Calculate days
            days_since_added = (now - date_added).days if date_added else None
            days_since_viewed = (now - last_viewed).days if last_viewed else None
            
            # Check criteria
            passes_grace = date_added and date_added <= grace_cutoff
            passes_inactivity = last_viewed and last_viewed <= inactivity_cutoff
            
            results.append({
                "title": item['title'],
                "type": item['type'],
                "date_added": date_added.isoformat() if date_added else None,
                "date_added_source": date_added_source,
                "days_since_added": days_since_added,
                "passes_grace_period": passes_grace,
                "grace_period_days": grace_days,
                "last_viewed": last_viewed.isoformat() if last_viewed else None,
                "last_viewed_source": last_viewed_source,
                "days_since_viewed": days_since_viewed,
                "view_count": view_count,
                "passes_inactivity": passes_inactivity,
                "inactivity_days": inactivity_days,
                "would_delete": passes_grace and passes_inactivity,
                "blocking_reason": (
                    "too_new" if not passes_grace else
                    "recently_watched" if not passes_inactivity else
                    None
                )
            })
        
        return {
            "criteria": {
                "grace_cutoff": grace_cutoff.isoformat(),
                "inactivity_cutoff": inactivity_cutoff.isoformat(),
                "grace_days": grace_days,
                "inactivity_days": inactivity_days
            },
            "total_checked": len(results),
            "would_delete": len([r for r in results if r['would_delete']]),
            "items": results
        }
    
    except Exception as e:
        logger.error(f"Debug endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tautulli-sync-status")
async def debug_tautulli_sync(
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Check how many items have Tautulli watch data populated.
    """
    try:
        # Count total items
        total_result = supabase.table('media_items')\
            .select('id', count='exact')\
            .execute()
        total_items = total_result.count or 0
        
        # Count items with Tautulli data
        with_tautulli = supabase.table('media_items')\
            .select('id', count='exact')\
            .not_.is_('last_watched_at', 'null')\
            .execute()
        items_with_data = with_tautulli.count or 0
        
        # Count items with views
        with_views = supabase.table('media_items')\
            .select('id', count='exact')\
            .gt('total_play_count', 0)\
            .execute()
        items_with_views = with_views.count or 0
        
        # Get sample of items WITH Tautulli data
        sample_with_data = supabase.table('media_items')\
            .select('title, type, last_watched_at, total_play_count, total_watch_time_seconds')\
            .not_.is_('last_watched_at', 'null')\
            .limit(5)\
            .execute()
        
        # Get sample of items WITHOUT Tautulli data
        sample_without_data = supabase.table('media_items')\
            .select('title, type, added_at')\
            .is_('last_watched_at', 'null')\
            .limit(5)\
            .execute()
        
        return {
            "total_items": total_items,
            "items_with_tautulli_data": items_with_data,
            "items_with_views": items_with_views,
            "percentage_synced": round((items_with_data / total_items * 100), 2) if total_items > 0 else 0,
            "tautulli_integration_exists": None,  # TODO: check integrations table
            "sample_items_with_data": sample_with_data.data or [],
            "sample_items_without_data": sample_without_data.data or []
        }
    
    except Exception as e:
        logger.error(f"Debug endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage-count-debug")
async def debug_storage_count(
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Debug storage count discrepancy.
    """
    try:
        # Count ALL items
        all_items = supabase.table('media_items')\
            .select('id', count='exact')\
            .execute()
        
        # Count items with file_size
        with_size = supabase.table('media_items')\
            .select('id', count='exact')\
            .not_.is_('file_size_bytes', 'null')\
            .execute()
        
        # Count by type
        by_type = {}
        for media_type in ['movie', 'show', 'season', 'episode']:
            result = supabase.table('media_items')\
                .select('id', count='exact')\
                .eq('type', media_type)\
                .execute()
            by_type[media_type] = result.count or 0
        
        return {
            "total_items": all_items.count or 0,
            "items_with_file_size": with_size.count or 0,
            "items_without_file_size": (all_items.count or 0) - (with_size.count or 0),
            "by_type": by_type
        }
    
    except Exception as e:
        logger.error(f"Debug endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
