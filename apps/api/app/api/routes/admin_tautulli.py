"""
Admin API routes for Tautulli synchronization.

Requires admin role for all endpoints.
"""

from datetime import datetime
from typing import Any, Dict, AsyncGenerator
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
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
        # Get server_id from integration
        server_id = integration.get("server_id")
        if not server_id:
            logger.warning("Integration missing server_id, skipping sync history log")
        else:
            sync_record = {
                "user_id": admin_user["id"],
                "server_id": server_id,
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


@router.get("/sync/tautulli/stream")
async def stream_tautulli_sync(
    days_back: int = Query(default=90, ge=1, le=365, description="Number of days of history to sync"),
    auth_token: str = Query(..., description="Supabase auth token for SSE"),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Stream Tautulli sync progress with Server-Sent Events (SSE).
    
    Similar to Plex sync streaming, this endpoint provides real-time
    progress updates during Tautulli history synchronization.
    
    **Requires admin role.**
    
    Note: EventSource doesn't support custom headers, so we pass auth token as query param.
    This is only for SSE endpoints where headers aren't supported.
    
    Event format:
    - status: "connecting", "syncing", "complete", "error"
    - current: number of items processed
    - total: estimated total items
    - message: status message
    - eta_seconds: estimated time remaining
    """
    
    # Validate auth token and check admin role since EventSource can't send Authorization header
    try:
        user_response = supabase.auth.get_user(auth_token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid auth token")
        
        # Get user details and check admin role
        user_result = supabase.table('users').select('*').eq('id', user_response.user.id).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        admin_user = user_result.data
        
        # Debug logging
        logger.info(f"User {user_response.user.id} role: {admin_user.get('role')}")
        
        # Check admin role
        if admin_user.get('role') != 'admin':
            logger.warning(f"User {user_response.user.id} denied access - role is '{admin_user.get('role')}', expected 'admin'")
            raise HTTPException(status_code=403, detail=f"Admin access required. Your role: {admin_user.get('role')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth validation failed: {e}")
        raise HTTPException(status_code=403, detail="Authentication failed")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send connecting status
            yield f"data: {json.dumps({'status': 'connecting', 'message': 'Connecting to Tautulli...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Get Tautulli integration
            integration_response = supabase.table("integrations")\
                .select("*")\
                .eq("service", "tautulli")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            
            if not integration_response.data or len(integration_response.data) == 0:
                yield f"data: {json.dumps({'status': 'error', 'message': 'No active Tautulli integration found'})}\n\n"
                return
            
            integration = integration_response.data[0]
            
            # Initialize services
            tautulli = TautulliService(
                url=integration["url"],
                api_key=integration["api_key"]
            )
            
            # Send counting status
            yield f"data: {json.dumps({'status': 'counting', 'message': 'Fetching watch history...'})}\n\n"
            
            started_at = datetime.utcnow()
            sync_service = TautulliSyncService(supabase, tautulli)
            
            # Track progress
            items_processed = 0
            items_updated = 0
            items_created = 0
            errors = []
            
            # Fetch history in batches and stream progress
            batch_size = 100
            offset = 0
            total_estimated = None
            
            while True:
                try:
                    # Fetch batch from Tautulli (API returns results in descending date order by default)
                    history_batch = await tautulli.get_history(
                        length=batch_size,
                        start=offset
                    )
                    
                    if not history_batch or "data" not in history_batch:
                        break
                    
                    records = history_batch.get("data", [])
                    if not records:
                        break
                    
                    # Update total estimate on first batch
                    if total_estimated is None:
                        total_estimated = history_batch.get("recordsTotal", len(records))
                    
                    # Process batch
                    batch_stats = await sync_service.process_history_batch(records)
                    items_processed += len(records)
                    items_updated += batch_stats.get("updated", 0)
                    items_created += batch_stats.get("created", 0)
                    
                    # Calculate ETA
                    elapsed = (datetime.utcnow() - started_at).total_seconds()
                    items_per_second = items_processed / elapsed if elapsed > 0 else 0
                    remaining = max(0, (total_estimated or 0) - items_processed)
                    eta_seconds = int(remaining / items_per_second) if items_per_second > 0 else 0
                    
                    # Send progress update
                    yield f"data: {json.dumps({'status': 'syncing', 'current': items_processed, 'total': total_estimated, 'eta_seconds': eta_seconds, 'items_per_second': round(items_per_second, 1), 'updated': items_updated, 'created': items_created})}\n\n"
                    
                    await asyncio.sleep(0.1)  # Small delay to not overwhelm client
                    
                    offset += batch_size
                    
                    # Stop if we've processed enough or reached the end
                    if len(records) < batch_size or offset >= (total_estimated or float('inf')):
                        break
                        
                except Exception as batch_error:
                    logger.error(f"Error processing batch: {batch_error}")
                    errors.append(str(batch_error))
                    continue
            
            # Complete
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            
            # Log to sync_history
            server_id = integration.get("server_id")
            if server_id:
                sync_record = {
                    "user_id": admin_user["id"],
                    "server_id": server_id,
                    "sync_type": "tautulli_aggregated_stats",
                    "status": "completed",
                    "items_processed": items_processed,
                    "items_updated": items_updated,
                    "items_added": items_created,
                    "items_removed": 0,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "metadata": {
                        "days_back": days_back,
                        "duration_seconds": duration,
                        "errors": errors
                    }
                }
                supabase.table("sync_history").insert(sync_record).execute()
            
            yield f"data: {json.dumps({'status': 'complete', 'current': items_processed, 'total': items_processed, 'duration_seconds': round(duration, 1), 'updated': items_updated, 'created': items_created, 'message': f'Synced {items_processed} history items in {duration:.1f}s'})}\n\n"
            
        except Exception as e:
            logger.error(f"Tautulli sync stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
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
