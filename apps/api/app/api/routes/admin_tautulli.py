"""
Admin API routes for Tautulli synchronization.

Requires admin role for all endpoints.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, require_admin
from app.core.logging import get_logger
from app.services.tautulli_sync import TautulliSyncService
from app.services.integrations.tautulli import TautulliService

router = APIRouter()
logger = get_logger("admin.tautulli_sync")


class TautulliSyncRequest(BaseModel):
    """Request to trigger Tautulli sync."""
    days_back: int = Field(default=90, ge=1, le=365, description="Number of days of history to sync")
    batch_size: int = Field(default=100, ge=10, le=500, description="Items per API call")


class TautulliSyncResponse(BaseModel):
    """Response from Tautulli sync operation."""
    success: bool
    started_at: str
    completed_at: str
    history_items_fetched: int
    media_items_updated: int
    media_items_created: int
    errors: list[str]
    message: str


@router.post("/sync/tautulli", response_model=TautulliSyncResponse)
async def trigger_tautulli_sync(
    request: TautulliSyncRequest,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
) -> TautulliSyncResponse:
    """
    Trigger Tautulli watch history synchronization.
    
    This endpoint:
    1. Fetches watch history from Tautulli API
    2. Aggregates statistics by media item across ALL Plex users
    3. Updates media_items table with server-wide metrics:
       - total_play_count
       - last_watched_at
       - total_watch_time_seconds
    
    These metrics are used by the deletion service to make accurate
    decisions based on ALL user activity, not just SmartPlex users.
    
    **Requires admin role.**
    
    Args:
        request: Sync configuration (days_back, batch_size)
        admin_user: Admin user from authentication
        supabase: Supabase client
        
    Returns:
        Sync statistics and results
    """
    try:
        logger.info(f"Admin {admin_user['email']} triggered Tautulli sync (days_back={request.days_back})")
        
        # Get Tautulli integration for this user
        integration_response = supabase.table("integrations")\
            .select("*")\
            .eq("service", "tautulli")\
            .eq("status", "active")\
            .limit(1)\
            .execute()
        
        if not integration_response.data or len(integration_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Tautulli integration found. Please configure Tautulli in integrations."
            )
        
        integration = integration_response.data[0]
        
        # Initialize Tautulli service
        tautulli = TautulliService(
            url=integration["url"],
            api_key=integration["api_key"]
        )
        
        # Initialize sync service
        sync_service = TautulliSyncService(supabase, tautulli)
        
        # Run sync
        sync_stats = await sync_service.sync_watch_history(
            days_back=request.days_back,
            batch_size=request.batch_size
        )
        
        # Log sync to database for history
        sync_record = {
            "user_id": admin_user["id"],
            "sync_type": "tautulli_aggregated_stats",
            "status": "completed" if sync_stats["success"] else "failed",
            "items_processed": sync_stats["history_items_fetched"],
            "items_updated": sync_stats["media_items_updated"],
            "items_added": sync_stats.get("media_items_created", 0),
            "items_removed": 0,
            "started_at": sync_stats["started_at"],
            "completed_at": sync_stats["completed_at"],
            "metadata": {
                "days_back": request.days_back,
                "batch_size": request.batch_size,
                "errors": sync_stats["errors"]
            }
        }
        
        supabase.table("sync_history").insert(sync_record).execute()
        
        message = f"Successfully synced {sync_stats['history_items_fetched']} history items"
        if sync_stats["errors"]:
            message += f" with {len(sync_stats['errors'])} errors"
        
        logger.info(message)
        
        return TautulliSyncResponse(
            success=sync_stats["success"],
            started_at=sync_stats["started_at"],
            completed_at=sync_stats["completed_at"],
            history_items_fetched=sync_stats["history_items_fetched"],
            media_items_updated=sync_stats["media_items_updated"],
            media_items_created=sync_stats.get("media_items_created", 0),
            errors=sync_stats["errors"],
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tautulli sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tautulli sync failed: {str(e)}"
        )


@router.get("/sync/tautulli/status")
async def get_tautulli_sync_status(
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get status of Tautulli synchronization.
    
    Returns information about:
    - Last sync timestamp
    - Number of media items with Tautulli stats
    - Recent sync history
    
    **Requires admin role.**
    
    Args:
        admin_user: Admin user from authentication
        supabase: Supabase client
        
    Returns:
        Sync status information
    """
    try:
        # Get last sync from sync_history
        last_sync = supabase.table("sync_history")\
            .select("*")\
            .eq("sync_type", "tautulli_aggregated_stats")\
            .order("completed_at", desc=True)\
            .limit(1)\
            .execute()
        
        # Count media items with Tautulli stats
        try:
            items_with_stats_result = supabase.table("media_items")\
                .select("id")\
                .not_.is_("tautulli_synced_at", "null")\
                .execute()
            items_with_stats_count = len(items_with_stats_result.data) if items_with_stats_result.data else 0
        except:
            items_with_stats_count = 0
        
        # Get total media items count
        try:
            total_items_result = supabase.table("media_items")\
                .select("id")\
                .execute()
            total_items_count = len(total_items_result.data) if total_items_result.data else 0
        except:
            total_items_count = 0
        
        coverage = round(
            (items_with_stats_count / total_items_count * 100) if total_items_count > 0 else 0,
            1
        )
        
        return {
            "last_sync": last_sync.data[0] if last_sync.data else None,
            "items_with_tautulli_stats": items_with_stats_count,
            "total_media_items": total_items_count,
            "coverage_percentage": coverage
        }
        
    except Exception as e:
        logger.error(f"Failed to get Tautulli sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )
