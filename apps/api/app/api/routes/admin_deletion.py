"""
Admin API routes for deletion management.

Requires admin role for all endpoints.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, require_admin
from app.core.logging import get_logger
from app.services.deletion_service import DeletionService
from app.services.cascade_deletion_service import CascadeDeletionService
from app.services.plex_collections import PlexCollectionManager

router = APIRouter()
logger = get_logger("admin.deletion")


# Request/Response Models
class DeletionRuleCreate(BaseModel):
    """Create a new deletion rule."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = False
    dry_run_mode: bool = True
    grace_period_days: int = Field(30, ge=0)
    inactivity_threshold_days: int = Field(15, ge=0)
    excluded_libraries: List[str] = Field(default_factory=list)
    excluded_genres: List[str] = Field(default_factory=list)
    excluded_collections: List[str] = Field(default_factory=list)
    min_rating: Optional[float] = Field(None, ge=0, le=10)


class DeletionRuleUpdate(BaseModel):
    """Update an existing deletion rule."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    dry_run_mode: Optional[bool] = None
    grace_period_days: Optional[int] = Field(None, ge=0)
    inactivity_threshold_days: Optional[int] = Field(None, ge=0)
    excluded_libraries: Optional[List[str]] = None
    excluded_genres: Optional[List[str]] = None
    excluded_collections: Optional[List[str]] = None
    min_rating: Optional[float] = Field(None, ge=0, le=10)


class DeletionRuleResponse(BaseModel):
    """Deletion rule response."""
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    dry_run_mode: bool
    grace_period_days: int
    inactivity_threshold_days: int
    excluded_libraries: List[str]
    excluded_genres: List[str]
    excluded_collections: List[str]
    min_rating: Optional[float]
    created_at: str
    updated_at: str
    last_run_at: Optional[str]
    next_run_at: Optional[str]


class ScanRequest(BaseModel):
    """Request to scan for deletion candidates."""
    rule_id: str
    dry_run: bool = True
    update_plex_collection: bool = True  # Auto-update "Leaving Soon" collection


class ExecuteDeletionRequest(BaseModel):
    """Request to execute deletion."""
    rule_id: str
    candidate_ids: Optional[List[str]] = None  # If None, deletes all candidates from last scan
    dry_run: bool = False
    plex_token: Optional[str] = None  # Plex token for deletion operations


@router.get("/rules", response_model=List[DeletionRuleResponse])
async def list_deletion_rules(
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all deletion rules.
    
    Requires admin role.
    """
    try:
        response = supabase.table("deletion_rules").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to fetch deletion rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch deletion rules"
        )


@router.get("/rules/{rule_id}", response_model=DeletionRuleResponse)
async def get_deletion_rule(
    rule_id: str,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get a specific deletion rule by ID.
    
    Requires admin role.
    """
    try:
        response = supabase.table("deletion_rules").select("*").eq("id", rule_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deletion rule {rule_id} not found"
            )
        
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch deletion rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch deletion rule"
        )


@router.post("/rules", response_model=DeletionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_deletion_rule(
    rule: DeletionRuleCreate,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create a new deletion rule.
    
    Requires admin role.
    """
    try:
        rule_data = rule.model_dump()
        rule_data["created_by"] = admin_user["id"]
        rule_data["updated_by"] = admin_user["id"]
        
        response = supabase.table("deletion_rules").insert(rule_data).execute()
        
        # Log audit trail
        supabase.table("audit_log").insert({
            "user_id": admin_user["id"],
            "action": "create",
            "resource_type": "deletion_rule",
            "resource_id": response.data[0]["id"],
            "changes": {"created": rule_data}
        }).execute()
        
        logger.info(f"Created deletion rule: {rule.name} by {admin_user['email']}")
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to create deletion rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deletion rule"
        )


@router.patch("/rules/{rule_id}", response_model=DeletionRuleResponse)
async def update_deletion_rule(
    rule_id: str,
    rule: DeletionRuleUpdate,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Update an existing deletion rule.
    
    Requires admin role.
    """
    try:
        # Fetch current rule for audit
        current = supabase.table("deletion_rules").select("*").eq("id", rule_id).single().execute()
        
        if not current.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deletion rule {rule_id} not found"
            )
        
        # Update only provided fields
        update_data = rule.model_dump(exclude_unset=True)
        update_data["updated_by"] = admin_user["id"]
        
        response = supabase.table("deletion_rules").update(update_data).eq("id", rule_id).execute()
        
        # Log audit trail
        supabase.table("audit_log").insert({
            "user_id": admin_user["id"],
            "action": "update",
            "resource_type": "deletion_rule",
            "resource_id": rule_id,
            "changes": {
                "before": current.data,
                "after": update_data
            }
        }).execute()
        
        logger.info(f"Updated deletion rule {rule_id} by {admin_user['email']}")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update deletion rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update deletion rule"
        )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deletion_rule(
    rule_id: str,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Delete a deletion rule.
    
    Requires admin role.
    """
    try:
        # Fetch rule for audit
        current = supabase.table("deletion_rules").select("*").eq("id", rule_id).single().execute()
        
        if not current.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deletion rule {rule_id} not found"
            )
        
        supabase.table("deletion_rules").delete().eq("id", rule_id).execute()
        
        # Log audit trail
        supabase.table("audit_log").insert({
            "user_id": admin_user["id"],
            "action": "delete",
            "resource_type": "deletion_rule",
            "resource_id": rule_id,
            "changes": {"deleted": current.data}
        }).execute()
        
        logger.info(f"Deleted deletion rule {rule_id} by {admin_user['email']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deletion rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deletion rule"
        )


@router.post("/scan")
async def scan_for_candidates(
    request: ScanRequest,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Scan for deletion candidates using a rule.
    
    This is always a dry-run that returns what would be deleted.
    Requires admin role.
    """
    try:
        deletion_service = DeletionService(supabase)
        candidates = await deletion_service.scan_for_candidates(
            rule_id=UUID(request.rule_id),
            dry_run=True
        )
        
        # Log audit trail
        supabase.table("audit_log").insert({
            "user_id": admin_user["id"],
            "action": "scan",
            "resource_type": "deletion_rule",
            "resource_id": request.rule_id,
            "changes": {
                "candidates_found": len(candidates),
                "dry_run": True
            }
        }).execute()
        
        logger.info(f"Scanned for candidates using rule {request.rule_id}: found {len(candidates)} items")
        
        # Update Plex "Leaving Soon" collection if requested
        collection_result = None
        if request.update_plex_collection and len(candidates) > 0:
            try:
                # Get user's server
                server_result = supabase.table("servers")\
                    .select("id")\
                    .eq("user_id", admin_user["id"])\
                    .limit(1)\
                    .execute()
                
                if server_result.data and len(server_result.data) > 0:
                    server_id = server_result.data[0]["id"]
                    
                    collection_manager = PlexCollectionManager(supabase)
                    collection_result = await collection_manager.update_leaving_soon_collection(
                        server_id=server_id,
                        user_id=admin_user["id"],
                        candidates=candidates,
                        dry_run=False
                    )
                    
                    logger.info(f"Updated Plex collection: {collection_result}")
            except Exception as coll_error:
                logger.error(f"Failed to update Plex collection (non-fatal): {coll_error}")
                collection_result = {"success": False, "error": str(coll_error)}
        
        return {
            "rule_id": request.rule_id,
            "total_candidates": len(candidates),
            "candidates": candidates,
            "plex_collection": collection_result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to scan for candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scan for deletion candidates"
        )


@router.post("/execute")
async def execute_deletion(
    request: ExecuteDeletionRequest,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Execute deletion of media items with CASCADE across all systems.
    
    If dry_run=True, this simulates the deletion without actually removing files.
    If dry_run=False, this will PERMANENTLY delete files from:
    - Plex library (actual file deletion)
    - Sonarr (prevents TV show re-download)
    - Radarr (prevents movie re-download)
    - Overseerr (clears request, allows re-request if needed)
    
    Requires admin role.
    """
    try:
        deletion_service = DeletionService(supabase)
        cascade_service = CascadeDeletionService(supabase)
        
        logger.info(f"🔍 Execute deletion request: rule_id={request.rule_id}, dry_run={request.dry_run}, candidate_ids={request.candidate_ids}")
        
        # CRITICAL FIX: If specific candidate_ids provided, ONLY delete those
        # Do NOT re-scan rule as library may have changed since user's scan
        if request.candidate_ids:
            # User selected specific items - fetch ONLY those from database
            logger.info(f"Deleting {len(request.candidate_ids)} specifically selected items (not re-scanning rule)")
            candidates = []
            for candidate_id in request.candidate_ids:
                try:
                    logger.info(f"  Fetching candidate {candidate_id} from database...")
                    media_result = supabase.table("media_items")\
                        .select("id, title, type, file_size_mb, plex_id, server_id, sonarr_series_id, radarr_movie_id, tmdb_id, tvdb_id, parent_title")\
                        .eq("id", candidate_id)\
                        .single()\
                        .execute()
                    
                    if media_result.data:
                        candidates.append(media_result.data)
                        logger.info(f"  ✅ Found: {media_result.data.get('title')}")
                    else:
                        logger.warning(f"  ❌ Candidate {candidate_id} not found in database")
                except Exception as e:
                    logger.error(f"  ❌ Error fetching candidate {candidate_id}: {e}")
        else:
            # No specific selection - scan rule for ALL matching candidates
            logger.info(f"No candidate_ids provided - scanning rule {request.rule_id} for all matches")
            candidates = await deletion_service.scan_for_candidates(
                rule_id=UUID(request.rule_id),
                dry_run=True
            )
        
        logger.info(f"📊 Total candidates prepared for deletion: {len(candidates)}")
        for idx, cand in enumerate(candidates[:5]):  # Log first 5
            logger.info(f"  {idx+1}. {cand.get('title', 'unknown')} (ID: {cand.get('id', 'unknown')})")
        
        if not candidates:
            return {
                "rule_id": request.rule_id,
                "message": "No candidates found for deletion",
                "results": {
                    "total_candidates": 0,
                    "deleted": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total_size_mb": 0
                }
            }
        
        # Process ALL candidates - no batch limit
        # Handle large batches by processing sequentially with proper error handling
        logger.info(f"Processing {len(candidates)} candidates for deletion...")
        
        # Execute CASCADE deletion on each candidate
        deletion_results = []
        deleted_count = 0
        failed_count = 0
        total_size_mb = 0.0
        
        for idx, candidate in enumerate(candidates):
            try:
                # Log progress every 5 items
                if idx % 5 == 0 and idx > 0:
                    logger.info(f"Progress: {idx}/{len(candidates)} processed ({deleted_count} deleted, {failed_count} failed)")
                
                # Get full media item data from database
                media_result = supabase.table("media_items")\
                    .select("*")\
                    .eq("id", candidate['id'])\
                    .single()\
                    .execute()
                
                if not media_result.data:
                    logger.warning(f"Media item {candidate['id']} not found in database")
                    failed_count += 1
                    deletion_results.append({
                        "media_item_id": candidate['id'],
                        "error": "Media item not found in database",
                        "overall_status": "failed"
                    })
                    continue
                
                media_item = media_result.data
                
                # Execute cascade deletion
                result = await cascade_service.delete_media_item(
                    media_item=media_item,
                    user_id=admin_user["id"],
                    deletion_rule_id=str(request.rule_id),
                    deletion_reason=f"rule_{request.rule_id}",
                    dry_run=request.dry_run,
                    plex_token=request.plex_token
                )
                
                deletion_results.append(result)
                
                if result["overall_status"] == "completed":
                    deleted_count += 1
                    total_size_mb += media_item.get('file_size_mb', 0) or 0
                elif result["overall_status"] == "partial":
                    deleted_count += 1  # Count partial as success since Plex deletion worked
                    total_size_mb += media_item.get('file_size_mb', 0) or 0
                else:
                    failed_count += 1
                
                # Small delay to prevent API rate limiting (0.1s per item)
                await asyncio.sleep(0.1)
                    
            except Exception as deletion_error:
                logger.error(f"Error deleting candidate {candidate.get('id', 'unknown')}: {deletion_error}", exc_info=True)
                failed_count += 1
                deletion_results.append({
                    "media_item_id": candidate.get('id', 'unknown'),
                    "media_title": candidate.get('title', 'unknown'),
                    "error": str(deletion_error),
                    "overall_status": "failed"
                })
        
        # Final progress log
        logger.info(f"✅ Deletion complete: {len(candidates)} total, {deleted_count} deleted, {failed_count} failed")
        
        # Log audit trail
        try:
            supabase.table("audit_log").insert({
                "user_id": admin_user["id"],
                "action": "execute_deletion" if not request.dry_run else "execute_deletion_dry_run",
                "resource_type": "deletion_rule",
                "resource_id": request.rule_id,
                "changes": {
                    "total_candidates": len(candidates),
                    "deleted": deleted_count,
                    "failed": failed_count,
                    "dry_run": request.dry_run,
                    "cascade_results": deletion_results
                }
            }).execute()
        except Exception as audit_error:
            logger.error(f"Failed to log audit trail (non-fatal): {audit_error}")
        
        action = "DRY RUN" if request.dry_run else "EXECUTED CASCADE DELETION"
        logger.warning(f"{action} using rule {request.rule_id}: deleted={deleted_count}, failed={failed_count}")
        
        # Return simplified results
        return {
            "rule_id": request.rule_id,
            "dry_run": request.dry_run,
            "results": {
                "total_candidates": len(candidates),
                "deleted": deleted_count,
                "failed": failed_count,
                "skipped": 0,
                "total_size_mb": round(total_size_mb, 2)
            },
            "cascade_details": deletion_results  # Include full cascade results for debugging
        }
    except ValueError as e:
        logger.error(f"ValueError in execute_deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to execute deletion: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute deletion: {str(e)}"
        )


@router.get("/history")
async def get_deletion_history(
    limit: int = 100,
    offset: int = 0,
    admin_user: Dict[str, Any] = Depends(require_admin),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get deletion history (audit trail).
    
    Requires admin role.
    """
    try:
        response = supabase.table("deletion_history")\
            .select("*")\
            .order("deleted_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return {
            "total": len(response.data),
            "limit": limit,
            "offset": offset,
            "items": response.data
        }
    except Exception as e:
        logger.error(f"Failed to fetch deletion history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch deletion history"
        )
