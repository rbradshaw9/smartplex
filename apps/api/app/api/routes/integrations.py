"""
Integration management API endpoints.
Provides CRUD operations for external service integrations.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client
from datetime import datetime
import logging

from app.core.supabase import get_current_user, get_supabase_client
from app.services.integrations import (
    TautulliService,
    SonarrService,
    RadarrService,
    OverseerrService,
    IntegrationException
)

router = APIRouter()
logger = logging.getLogger(__name__)


class IntegrationCreate(BaseModel):
    """Model for creating a new integration."""
    service: str = Field(..., description="Service name (tautulli, sonarr, radarr, overseerr)")
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name")
    url: str = Field(..., description="Service URL")
    api_key: str = Field(..., min_length=1, description="API key")
    server_id: str | None = Field(None, description="Associated server ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class IntegrationUpdate(BaseModel):
    """Model for updating an integration."""
    name: str | None = Field(None, min_length=1, max_length=100)
    url: str | None = None
    api_key: str | None = None
    status: str | None = Field(None, pattern="^(active|inactive|error)$")
    config: Dict[str, Any] | None = None


class IntegrationResponse(BaseModel):
    """Model for integration response."""
    id: str
    service: str
    name: str
    url: str
    status: str
    last_sync_at: str | None
    created_at: str
    updated_at: str
    config: Dict[str, Any]


def _get_integration_service(service: str, url: str, api_key: str):
    """Factory function to create integration service instances."""
    services = {
        'tautulli': TautulliService,
        'sonarr': SonarrService,
        'radarr': RadarrService,
        'overseerr': OverseerrService
    }
    
    service_class = services.get(service)
    if not service_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown service: {service}"
        )
    
    return service_class(url=url, api_key=api_key)


@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all integrations for the current user.
    """
    try:
        result = supabase.table('integrations')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Error fetching integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch integrations"
        )


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get a specific integration by ID.
    """
    try:
        result = supabase.table('integrations')\
            .select('*')\
            .eq('id', integration_id)\
            .eq('user_id', current_user['id'])\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch integration"
        )


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration: IntegrationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create a new integration.
    """
    try:
        # Validate service name
        valid_services = ['tautulli', 'sonarr', 'radarr', 'overseerr']
        if integration.service not in valid_services:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service. Must be one of: {', '.join(valid_services)}"
            )
        
        # Insert integration into database
        result = supabase.table('integrations').insert({
            'user_id': current_user['id'],
            'server_id': integration.server_id,
            'service': integration.service,
            'name': integration.name,
            'url': integration.url.rstrip('/'),
            'api_key': integration.api_key,  # TODO: Encrypt this
            'config': integration.config,
            'status': 'inactive'
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create integration"
            )
        
        # Log the action
        supabase.table('audit_log').insert({
            'user_id': current_user['id'],
            'action': 'create',
            'resource_type': 'integration',
            'resource_id': result.data[0]['id'],
            'changes': {
                'service': integration.service,
                'name': integration.name
            }
        }).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create integration: {str(e)}"
        )


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    updates: IntegrationUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Update an existing integration.
    """
    try:
        # Check if integration exists and belongs to user
        existing = supabase.table('integrations')\
            .select('*')\
            .eq('id', integration_id)\
            .eq('user_id', current_user['id'])\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Prepare update data
        update_data = updates.model_dump(exclude_unset=True)
        if 'url' in update_data and update_data['url']:
            update_data['url'] = update_data['url'].rstrip('/')
        
        # Update integration
        result = supabase.table('integrations')\
            .update(update_data)\
            .eq('id', integration_id)\
            .execute()
        
        # Log the action
        supabase.table('audit_log').insert({
            'user_id': current_user['id'],
            'action': 'update',
            'resource_type': 'integration',
            'resource_id': integration_id,
            'changes': update_data
        }).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update integration"
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Delete an integration.
    """
    try:
        # Check if integration exists and belongs to user
        existing = supabase.table('integrations')\
            .select('*')\
            .eq('id', integration_id)\
            .eq('user_id', current_user['id'])\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Delete integration
        supabase.table('integrations')\
            .delete()\
            .eq('id', integration_id)\
            .execute()
        
        # Log the action
        supabase.table('audit_log').insert({
            'user_id': current_user['id'],
            'action': 'delete',
            'resource_type': 'integration',
            'resource_id': integration_id,
            'changes': {
                'service': existing.data[0]['service'],
                'name': existing.data[0]['name']
            }
        }).execute()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration"
        )


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Test connection to an integration.
    """
    try:
        # Get integration
        result = supabase.table('integrations')\
            .select('*')\
            .eq('id', integration_id)\
            .eq('user_id', current_user['id'])\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        integration = result.data[0]
        
        # Create service instance and test connection
        service = _get_integration_service(
            integration['service'],
            integration['url'],
            integration['api_key']
        )
        
        async with service:
            test_result = await service.test_connection()
        
        # Update integration status based on test result
        new_status = 'active' if test_result['status'] == 'online' else 'error'
        supabase.table('integrations')\
            .update({'status': new_status, 'last_sync_at': datetime.utcnow().isoformat()})\
            .eq('id', integration_id)\
            .execute()
        
        return {
            'success': test_result['status'] == 'online',
            'details': test_result
        }
        
    except IntegrationException as e:
        # Update status to error
        supabase.table('integrations')\
            .update({'status': 'error'})\
            .eq('id', integration_id)\
            .execute()
        
        return {
            'success': False,
            'error': e.message,
            'service': e.service
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test integration: {str(e)}"
        )


@router.get("/{integration_id}/health")
async def get_integration_health(
    integration_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get health status of an integration without updating it.
    """
    try:
        result = supabase.table('integrations')\
            .select('*')\
            .eq('id', integration_id)\
            .eq('user_id', current_user['id'])\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        integration = result.data[0]
        
        return {
            'id': integration['id'],
            'name': integration['name'],
            'service': integration['service'],
            'status': integration['status'],
            'last_sync_at': integration['last_sync_at'],
            'url': integration['url']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration health"
        )
