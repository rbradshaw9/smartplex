"""
Watch List API Routes.

Allows users to save AI-recommended content for later viewing.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("watch_list")


class WatchListAddRequest(BaseModel):
    """Request to add item to watch list."""
    media_item_id: UUID = Field(..., description="UUID of media_item to add")
    priority: int = Field(5, ge=0, le=10, description="Priority 0-10 (higher = more urgent)")
    notes: Optional[str] = Field(None, description="Optional notes or AI recommendation context")


class WatchListUpdateRequest(BaseModel):
    """Request to update watch list item."""
    priority: Optional[int] = Field(None, ge=0, le=10, description="Update priority 0-10")
    notes: Optional[str] = Field(None, description="Update notes")


@router.post("")
async def add_to_watch_list(
    item: WatchListAddRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Add media item to user's watch list.
    
    - **media_item_id**: UUID of existing media_item from Plex library
    - **priority**: 0-10 (0=lowest, 10=highest urgency)
    - **notes**: Optional context like "AI recommended for mood: thriller"
    
    Returns the created watch list entry with full media details.
    """
    try:
        # Verify media item exists
        media_check = supabase.table("media_items")\
            .select("id, title")\
            .eq("id", str(item.media_item_id))\
            .maybe_single()\
            .execute()
        
        if not media_check.data:
            raise HTTPException(
                status_code=404,
                detail=f"Media item {item.media_item_id} not found"
            )
        
        # Add to watch list
        result = supabase.table("watch_list")\
            .insert({
                "user_id": user['id'],
                "media_item_id": str(item.media_item_id),
                "priority": item.priority,
                "notes": item.notes
            })\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=400,
                detail="Failed to add to watch list"
            )
        
        # Return with full details
        watch_list_item = supabase.rpc(
            "get_watch_list_item",
            {"p_watch_list_id": result.data[0]['id']}
        ).execute()
        
        if watch_list_item.data:
            return watch_list_item.data[0]
        
        return result.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        # Check for unique constraint violation
        if "duplicate key" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="Item already in watch list"
            )
        
        logger.error(f"Failed to add to watch list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_watch_list(
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    priority_min: Optional[int] = Query(None, ge=0, le=10, description="Filter by minimum priority"),
    unwatched_only: bool = Query(False, description="Show only unwatched items")
):
    """
    Get user's watch list with full media details.
    
    Returns items sorted by priority (desc), then added_at (desc).
    
    Query parameters:
    - **priority_min**: Only show items with priority >= this value
    - **unwatched_only**: Filter to only unwatched items
    """
    try:
        # Use the view for optimized query
        query = supabase.table("watch_list_with_details")\
            .select("*")\
            .eq("user_id", user['id'])
        
        if priority_min is not None:
            query = query.gte("priority", priority_min)
        
        if unwatched_only:
            query = query.eq("is_unwatched", True)
        
        result = query.execute()
        
        return {
            "items": result.data or [],
            "total": len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get watch list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{watch_list_id}")
async def get_watch_list_item(
    watch_list_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Get single watch list item with full media details."""
    try:
        result = supabase.table("watch_list_with_details")\
            .select("*")\
            .eq("id", str(watch_list_id))\
            .eq("user_id", user['id'])\
            .maybe_single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Watch list item not found")
        
        return result.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get watch list item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{watch_list_id}")
async def update_watch_list_item(
    watch_list_id: UUID,
    updates: WatchListUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Update watch list item priority or notes.
    
    Only provide fields you want to update.
    """
    try:
        # Verify ownership
        existing = supabase.table("watch_list")\
            .select("id")\
            .eq("id", str(watch_list_id))\
            .eq("user_id", user['id'])\
            .maybe_single()\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=404,
                detail="Watch list item not found"
            )
        
        # Build update dict
        update_data = {}
        if updates.priority is not None:
            update_data["priority"] = updates.priority
        if updates.notes is not None:
            update_data["notes"] = updates.notes
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No updates provided"
            )
        
        # Update
        result = supabase.table("watch_list")\
            .update(update_data)\
            .eq("id", str(watch_list_id))\
            .eq("user_id", user['id'])\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=400,
                detail="Failed to update watch list item"
            )
        
        return result.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watch list item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{watch_list_id}")
async def remove_from_watch_list(
    watch_list_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Remove item from watch list."""
    try:
        result = supabase.table("watch_list")\
            .delete()\
            .eq("id", str(watch_list_id))\
            .eq("user_id", user['id'])\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Watch list item not found"
            )
        
        return {
            "message": "Removed from watch list",
            "deleted_id": str(watch_list_id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from watch list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def clear_watch_list(
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    confirm: bool = Query(False, description="Must be true to confirm deletion")
):
    """
    Clear entire watch list for user.
    
    Requires confirm=true query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to clear watch list"
        )
    
    try:
        result = supabase.table("watch_list")\
            .delete()\
            .eq("user_id", user['id'])\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        
        return {
            "message": f"Cleared {deleted_count} items from watch list",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Failed to clear watch list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
