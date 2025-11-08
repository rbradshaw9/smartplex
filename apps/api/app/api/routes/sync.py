"""
Plex synchronization endpoints for SmartPlex API.
Handles syncing media libraries, user data, and watch statistics.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user
from app.core.exceptions import ValidationException, ExternalAPIException

router = APIRouter()


class PlexServerInfo(BaseModel):
    """Plex server information for sync requests."""
    name: str = Field(..., description="Plex server name")
    url: str = Field(..., description="Plex server URL")
    token: str = Field(..., description="Plex access token")
    machine_id: Optional[str] = Field(None, description="Plex machine identifier")


class SyncResponse(BaseModel):
    """Response model for sync operations."""
    success: bool
    message: str
    sync_id: str
    items_processed: int
    items_added: int
    items_updated: int
    errors: List[str] = []


@router.post("/plex")
async def sync_plex_library(
    server_info: PlexServerInfo,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> SyncResponse:
    """
    Sync Plex media library with SmartPlex database.
    
    This endpoint:
    1. Connects to specified Plex server
    2. Fetches library metadata
    3. Updates SmartPlex database with media items
    4. Records sync statistics
    
    Args:
        server_info: Plex server connection details
        current_user: Authenticated user information
        supabase: Supabase client for database operations
        
    Returns:
        Sync operation results and statistics
    """
    try:
        # Generate unique sync ID for tracking
        sync_id = f"sync_{current_user['id']}_{int(datetime.utcnow().timestamp())}"
        
        # Mock Plex API integration - in production, this would:
        # 1. Validate Plex server connection
        # 2. Fetch library sections
        # 3. Get media items and metadata
        # 4. Update database with normalized data
        
        # Mock sync data for demo
        mock_media_items = [
            {
                "title": "The Batman",
                "type": "movie",
                "year": 2022,
                "imdb_id": "tt1877830",
                "tmdb_id": 414906,
                "library_section": "Movies",
            },
            {
                "title": "House of the Dragon",
                "type": "series", 
                "year": 2022,
                "tmdb_id": 94997,
                "library_section": "TV Shows",
            },
            {
                "title": "Dune: Part One",
                "type": "movie",
                "year": 2021,
                "imdb_id": "tt1160419",
                "tmdb_id": 438631,
                "library_section": "Movies",
            },
        ]
        
        # Store sync record in database
        sync_record = {
            "id": sync_id,
            "user_id": current_user["id"],
            "server_name": server_info.name,
            "server_url": server_info.url,
            "status": "completed",
            "items_processed": len(mock_media_items),
            "items_added": len(mock_media_items),
            "items_updated": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        # Insert sync record (mock operation)
        # In production: supabase.table("sync_history").insert(sync_record).execute()
        
        return SyncResponse(
            success=True,
            message=f"Successfully synced {len(mock_media_items)} media items from {server_info.name}",
            sync_id=sync_id,
            items_processed=len(mock_media_items),
            items_added=len(mock_media_items),
            items_updated=0,
            errors=[]
        )
        
    except Exception as e:
        raise ExternalAPIException(
            message="Failed to sync Plex library",
            details=str(e)
        )


@router.get("/history")
async def get_sync_history(
    limit: int = Field(default=10, ge=1, le=100, description="Max 100 records"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> List[Dict[str, Any]]:
    """
    Get sync history for the current user.
    
    Args:
        limit: Maximum number of sync records to return
        current_user: Authenticated user information
        supabase: Supabase client for database operations
        
    Returns:
        List of sync history records
    """
    try:
        # Mock sync history - in production, fetch from database
        mock_history = [
            {
                "id": "sync_user123_1704067200",
                "server_name": "Main Plex Server",
                "status": "completed",
                "items_processed": 1247,
                "items_added": 23,
                "items_updated": 8,
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:32Z",
            },
            {
                "id": "sync_user123_1703980800", 
                "server_name": "Main Plex Server",
                "status": "completed",
                "items_processed": 1224,
                "items_added": 0,
                "items_updated": 15,
                "started_at": "2023-12-31T00:00:00Z",
                "completed_at": "2023-12-31T00:03:45Z",
            }
        ]
        
        return mock_history[:limit]
        
    except Exception as e:
        raise ExternalAPIException(
            message="Failed to fetch sync history",
            details=str(e)
        )