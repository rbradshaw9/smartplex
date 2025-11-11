"""
System Configuration API Routes.

Manages global system settings like storage capacity, sync schedules, etc.
Admin-only endpoints for system configuration.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("system_config")


class StorageQualityBreakdown(BaseModel):
    """Storage breakdown by quality."""
    video_resolution: Optional[str]
    video_codec: Optional[str]
    container: Optional[str]
    item_count: int
    total_gb: float
    avg_bitrate_kbps: Optional[float]
    avg_size_gb: float


class StorageCapacityConfig(BaseModel):
    """Storage capacity configuration."""
    total_gb: float = Field(..., description="Total storage capacity in GB", gt=0)
    source: str = Field(default="manual", description="Source of capacity data (manual, api, ssh)")
    notes: Optional[str] = Field(None, description="Additional notes about storage configuration")


class SystemConfigResponse(BaseModel):
    """System configuration response."""
    key: str
    value: Dict[str, Any]
    description: Optional[str]
    updated_at: str
    updated_by: Optional[str]


@router.get("/config/storage-capacity")
async def get_storage_capacity(
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get storage capacity configuration.
    
    Returns:
        Storage capacity settings including total GB and metadata
    """
    try:
        result = supabase.table('system_config')\
            .select('key, value, description, updated_at, updated_by')\
            .eq('key', 'storage_capacity')\
            .execute()
        
        if not result.data or len(result.data) == 0:
            # Return default if not configured
            return {
                "total_gb": 10000,
                "source": "manual",
                "notes": "Default capacity. Update with actual storage size.",
                "configured": False
            }
        
        config = result.data[0]
        capacity_data = config['value']
        capacity_data['configured'] = True
        capacity_data['updated_at'] = config.get('updated_at')
        
        return capacity_data
        
    except Exception as e:
        logger.error(f"Error fetching storage capacity config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch storage capacity: {str(e)}")


@router.put("/config/storage-capacity")
async def update_storage_capacity(
    config: StorageCapacityConfig,
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> SystemConfigResponse:
    """
    Update storage capacity configuration.
    
    Admin-only endpoint to set total storage capacity.
    
    Args:
        config: Storage capacity configuration
        
    Returns:
        Updated configuration
    """
    # Check if user is admin
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Validate capacity is greater than current usage
        storage_query = supabase.table('media_items')\
            .select('file_size_bytes')\
            .not_.is_('file_size_bytes', 'null')\
            .execute()
        
        total_size_bytes = sum(item.get('file_size_bytes', 0) or 0 for item in (storage_query.data or []))  # type: ignore
        current_used_gb = round(total_size_bytes / (1024 * 1024 * 1024), 2)
        
        if config.total_gb < current_used_gb:
            raise HTTPException(
                status_code=400, 
                detail=f"Storage capacity ({config.total_gb}GB) cannot be less than current usage ({current_used_gb}GB)"
            )
        
        config_data = {
            'key': 'storage_capacity',
            'value': config.model_dump(),
            'description': 'Total storage capacity in GB for media library. Manually configured by admin.',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_by': user['id']
        }
        
        result = supabase.table('system_config').upsert(
            config_data,
            on_conflict='key'
        ).execute()
        
        if not result.data or len(result.data) == 0:  # type: ignore
            raise HTTPException(status_code=500, detail="Failed to update storage capacity")
        
        updated = result.data[0]  # type: ignore
        
        logger.info(f"Storage capacity updated to {config.total_gb}GB by {user.get('email')}")
        
        return SystemConfigResponse(
            key=updated['key'],  # type: ignore
            value=updated['value'],  # type: ignore
            description=updated.get('description'),  # type: ignore
            updated_at=updated['updated_at'],  # type: ignore
            updated_by=updated.get('updated_by')  # type: ignore
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating storage capacity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update storage capacity: {str(e)}")


@router.get("/config")
async def get_all_config(
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all system configuration.
    
    Admin-only endpoint to view all system settings.
    
    Returns:
        Dictionary of all system configuration keys and values
    """
    # Check if user is admin
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = supabase.table('system_config')\
            .select('key, value, description, updated_at')\
            .execute()
        
        # Convert to dictionary keyed by config key
        config_dict = {}
        for item in result.data:  # type: ignore
            config_dict[item['key']] = {  # type: ignore
                'value': item['value'],  # type: ignore
                'description': item.get('description'),  # type: ignore
                'updated_at': item.get('updated_at')  # type: ignore
            }
        
        return config_dict
        
    except Exception as e:
        logger.error(f"Error fetching system config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system config: {str(e)}")


@router.get("/config/{key}")
async def get_config_by_key(
    key: str,
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> SystemConfigResponse:
    """
    Get specific system configuration by key.
    
    Args:
        key: Configuration key
        
    Returns:
        Configuration value and metadata
    """
    try:
        result = supabase.table('system_config')\
            .select('key, value, description, updated_at, updated_by')\
            .eq('key', key)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")
        
        config = result.data[0]
        
        return SystemConfigResponse(
            key=config['key'],
            value=config['value'],
            description=config.get('description'),
            updated_at=config['updated_at'],
            updated_by=config.get('updated_by')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching config key {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch config: {str(e)}")


@router.get("/storage/quality-analysis")
async def get_storage_quality_analysis(
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get storage breakdown by quality (resolution, codec, container).
    
    Returns storage optimization insights like:
    - H.264 vs HEVC compression opportunities
    - 4K vs 1080p vs 720p distribution
    - Container format breakdown
    
    Admin-only endpoint.
    """
    # Check if user is admin
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Query the storage_quality_analysis view
        result = supabase.table('storage_quality_analysis')\
            .select('*')\
            .execute()
        
        breakdowns = result.data or []  # type: ignore
        
        # Calculate totals and insights
        total_items = sum(b.get('item_count', 0) for b in breakdowns)  # type: ignore
        total_gb = sum(b.get('total_gb', 0) for b in breakdowns)  # type: ignore
        
        # Group by codec for compression insights
        codec_breakdown = {}
        for item in breakdowns:
            codec = item.get('video_codec', 'unknown')
            if codec not in codec_breakdown:
                codec_breakdown[codec] = {'count': 0, 'total_gb': 0}
            codec_breakdown[codec]['count'] += item.get('item_count', 0)
            codec_breakdown[codec]['total_gb'] += item.get('total_gb', 0)
        
        # Group by resolution
        resolution_breakdown = {}
        for item in breakdowns:
            res = item.get('video_resolution', 'unknown')
            if res not in resolution_breakdown:
                resolution_breakdown[res] = {'count': 0, 'total_gb': 0}
            resolution_breakdown[res]['count'] += item.get('item_count', 0)
            resolution_breakdown[res]['total_gb'] += item.get('total_gb', 0)
        
        # Calculate H.264 to HEVC potential savings (HEVC is ~40% smaller)
        h264_gb = codec_breakdown.get('h264', {}).get('total_gb', 0)
        hevc_savings_estimate_gb = round(h264_gb * 0.4, 2) if h264_gb > 0 else 0
        
        return {
            "summary": {
                "total_items": total_items,
                "total_gb": round(total_gb, 2),
                "unique_combinations": len(breakdowns)
            },
            "by_codec": codec_breakdown,
            "by_resolution": resolution_breakdown,
            "insights": {
                "h264_to_hevc_savings_gb": hevc_savings_estimate_gb,
                "h264_percentage": round((h264_gb / total_gb * 100), 1) if total_gb > 0 else 0,
                "hevc_percentage": round((codec_breakdown.get('hevc', {}).get('total_gb', 0) / total_gb * 100), 1) if total_gb > 0 else 0
            },
            "detailed_breakdown": breakdowns
        }
        
    except Exception as e:
        logger.error(f"Error fetching storage quality analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality analysis: {str(e)}")


@router.get("/storage/inaccessible-files")
async def get_inaccessible_files(
    supabase: Client = Depends(get_supabase_client),
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get list of broken/missing files.
    
    Returns files marked as inaccessible during sync.
    Useful for identifying storage issues and cleanup opportunities.
    
    Admin-only endpoint.
    """
    # Check if user is admin
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Query the inaccessible_files view
        result = supabase.table('inaccessible_files')\
            .select('*')\
            .execute()
        
        files = result.data or []
        total_wasted_gb = sum(f.get('size_gb', 0) for f in files)
        
        return {
            "total_inaccessible": len(files),
            "total_wasted_gb": round(total_wasted_gb, 2),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Error fetching inaccessible files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch inaccessible files: {str(e)}")
