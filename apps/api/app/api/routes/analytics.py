"""
Analytics API Routes with Hybrid Data Source Support.

Provides endpoints for syncing and querying watch analytics.
Automatically uses Tautulli when available, falls back to Plex API.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user
from app.services.analytics_service import AnalyticsService, DataSource
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("analytics_routes")


@router.get("/data-source")
async def get_analytics_data_source(
    server_id: str = Query(..., description="Server UUID"),
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Check which analytics data source is available.
    
    Returns "tautulli", "plex_api", or "none".
    Used by UI to show appropriate messaging.
    """
    try:
        analytics = AnalyticsService(supabase)
        data_source = await analytics.get_data_source(server_id)
        
        return {
            "server_id": server_id,
            "data_source": data_source,
            "capabilities": {
                "per_user_detail": data_source == "tautulli",
                "aggregate_only": data_source == "plex_api",
                "no_data": data_source == "none"
            },
            "recommendations": {
                "tautulli": "Full analytics with per-user breakdowns",
                "plex_api": "Aggregate data only. Install Tautulli for detailed analytics.",
                "none": "No watch data available. Configure Tautulli or sync Plex library."
            }[data_source]
        }
    
    except Exception as e:
        logger.error(f"Failed to check data source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/plex-aggregate")
async def sync_plex_aggregate_data(
    server_id: str = Query(..., description="Server UUID"),
    plex_token: str = Query(..., description="Plex authentication token"),
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Sync aggregate watch data from Plex API.
    
    Updates media_items with viewCount and lastViewedAt.
    Use this when Tautulli is not available.
    
    Note: This provides aggregate data only (all users combined).
    Install Tautulli for per-user analytics.
    """
    try:
        analytics = AnalyticsService(supabase)
        
        # Check if user has access to this server
        server_result = supabase.table("servers")\
            .select("*")\
            .eq("id", server_id)\
            .single()\
            .execute()
        
        if not server_result.data:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Only server owner/admin can sync
        if server_result.data['user_id'] != user['id'] and user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Only server admin can sync analytics")
        
        result = await analytics.sync_plex_aggregate_with_token(
            server_id=server_id,
            plex_token=plex_token,
            user_id=user['id']
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plex aggregate sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_analytics_status(
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get analytics status for all user's servers.
    
    Returns data source and capabilities for each server.
    """
    try:
        # Get user's servers
        servers_result = supabase.table("servers")\
            .select("id, name")\
            .eq("user_id", user['id'])\
            .execute()
        
        if not servers_result.data:
            return {"servers": []}
        
        analytics = AnalyticsService(supabase)
        
        status_list = []
        for server in servers_result.data:
            data_source = await analytics.get_data_source(server['id'])
            
            status_list.append({
                "server_id": server['id'],
                "server_name": server['name'],
                "data_source": data_source,
                "has_detailed_analytics": data_source == "tautulli",
                "has_aggregate_data": data_source in ["tautulli", "plex_api"]
            })
        
        return {"servers": status_list}
    
    except Exception as e:
        logger.error(f"Failed to get analytics status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
