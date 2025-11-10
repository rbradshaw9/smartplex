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
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
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
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = supabase.table('system_config')\
            .select('key, value, description, updated_at')\
            .execute()
        
        # Convert to dictionary keyed by config key
        config_dict = {}
        for item in result.data:
            config_dict[item['key']] = {
                'value': item['value'],
                'description': item.get('description'),
                'updated_at': item.get('updated_at')
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
