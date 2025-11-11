"""
Integration management API endpoints.
Provides CRUD operations for external service integrations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client
from datetime import datetime, timezone
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


# ============================================
# Overseerr-specific endpoints
# ============================================

@router.get("/overseerr/status")
async def get_overseerr_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Check if user has an active Overseerr integration.
    
    Use this to determine if request buttons should be shown in the UI.
    
    Args:
        current_user: Authenticated user
        supabase: Database client
        
    Returns:
        Integration status
    """
    try:
        result = supabase.table('integrations')\
            .select('id, name, status')\
            .eq('user_id', current_user['id'])\
            .eq('service', 'overseerr')\
            .eq('status', 'active')\
            .limit(1)\
            .execute()
        
        return {
            "available": bool(result.data),
            "integration": result.data[0] if result.data else None
        }
    except Exception as e:
        logger.error(f"Error checking Overseerr status: {e}")
        return {"available": False, "integration": None}


class OverseerrSearchRequest(BaseModel):
    """Request model for Overseerr search."""
    query: str = Field(..., min_length=1, description="Search query")


class OverseerrRequestCreate(BaseModel):
    """Request model for creating Overseerr request."""
    media_type: str = Field(..., pattern="^(movie|tv)$", description="Media type")
    media_id: int = Field(..., description="TMDB ID")
    title: Optional[str] = Field(None, description="Media title for logging")
    seasons: List[int] | None = Field(None, description="Season numbers for TV shows")
    is_4k: bool = Field(default=False, description="Request 4K quality")
    overseerr_user_id: int | None = Field(None, description="Overseerr user ID (optional, will try to find by email if not provided)")


@router.get("/overseerr/search")
async def search_overseerr(
    query: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Search for media in Overseerr/TMDB.
    
    Args:
        query: Search query
        current_user: Authenticated user
        supabase: Database client
        
    Returns:
        Search results from TMDB
    """
    try:
        # Get user's Overseerr integration
        result = supabase.table('integrations')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .eq('service', 'overseerr')\
            .eq('status', 'active')\
            .limit(1)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Overseerr integration found. Please configure Overseerr in admin settings."
            )
        
        integration = result.data[0]
        overseerr = OverseerrService(
            url=integration['url'],
            api_key=integration['api_key']
        )
        
        search_results = await overseerr.search_media(query)
        return search_results
        
    except HTTPException:
        raise
    except IntegrationException as e:
        logger.error(f"Overseerr search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Overseerr search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error searching Overseerr: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search media"
        )


@router.get("/overseerr/requests")
async def get_overseerr_requests(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get user's Overseerr request history.
    
    Args:
        limit: Maximum number of requests to return
        current_user: Authenticated user
        supabase: Database client
        
    Returns:
        List of requests with status
    """
    try:
        result = supabase.table('overseerr_requests')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .order('requested_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "requests": result.data or [],
            "count": len(result.data) if result.data else 0
        }
    except Exception as e:
        logger.error(f"Error fetching Overseerr requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch request history"
        )


@router.post("/overseerr/request")
async def create_overseerr_request(
    request_data: OverseerrRequestCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create a media request in Overseerr.
    
    Args:
        request_data: Request details
        current_user: Authenticated user
        supabase: Database client
        
    Returns:
        Created request information
    """
    try:
        # Get user's Overseerr integration
        result = supabase.table('integrations')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .eq('service', 'overseerr')\
            .eq('status', 'active')\
            .limit(1)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Overseerr integration found. Please configure Overseerr in admin settings."
            )
        
        integration = result.data[0]
        overseerr = OverseerrService(
            url=integration['url'],
            api_key=integration['api_key']
        )
        
        # Try to find the user's Overseerr ID
        overseerr_user_id = request_data.overseerr_user_id
        
        if not overseerr_user_id:
            # Try to find user by email in Overseerr
            try:
                users_response = await overseerr.get_users()
                if users_response and 'results' in users_response:
                    # Find user by email match
                    user_email = current_user.get('email', '').lower()
                    for overseerr_user in users_response['results']:
                        if overseerr_user.get('email', '').lower() == user_email:
                            overseerr_user_id = overseerr_user.get('id')
                            logger.info(f"Found Overseerr user ID {overseerr_user_id} for email {user_email}")
                            break
                    
                    # If user not found, trigger Plex user import
                    if not overseerr_user_id:
                        logger.info(f"User {user_email} not found in Overseerr, triggering Plex user import")
                        try:
                            import_result = await overseerr.import_plex_users()
                            logger.info(f"Plex user import result: {import_result}")
                            
                            # Try finding the user again after import
                            users_response = await overseerr.get_users()
                            if users_response and 'results' in users_response:
                                for overseerr_user in users_response['results']:
                                    if overseerr_user.get('email', '').lower() == user_email:
                                        overseerr_user_id = overseerr_user.get('id')
                                        logger.info(f"Found Overseerr user ID {overseerr_user_id} after import")
                                        break
                        except Exception as import_error:
                            logger.warning(f"Could not import Plex users to Overseerr: {import_error}")
                            # Continue anyway - request will be attributed to admin
            except Exception as user_lookup_error:
                logger.warning(f"Could not look up Overseerr user: {user_lookup_error}")
        
        # Create the request
        request_result = await overseerr.create_request(
            media_type=request_data.media_type,
            media_id=request_data.media_id,
            seasons=request_data.seasons,
            is_4k=request_data.is_4k,
            user_id=overseerr_user_id
        )
        
        # If we found the user ID and didn't have it before, store it for future requests
        if overseerr_user_id and not request_data.overseerr_user_id:
            try:
                supabase.table('users')\
                    .update({'overseerr_user_id': overseerr_user_id})\
                    .eq('id', current_user['id'])\
                    .execute()
            except Exception as update_error:
                logger.warning(f"Could not store Overseerr user ID: {update_error}")
        
        # Log the request to our database for tracking
        try:
            request_log = {
                "user_id": current_user['id'],
                "overseerr_user_id": overseerr_user_id,
                "media_title": request_data.title or f"{request_data.media_type} {request_data.media_id}",
                "media_type": request_data.media_type,
                "tmdb_id": request_data.media_id,
                "seasons": request_data.seasons,
                "overseerr_request_id": request_result.get('id') if isinstance(request_result, dict) else None,
                "overseerr_status": request_result.get('status', 'pending') if isinstance(request_result, dict) else 'pending',
                "requested_at": datetime.now(timezone.utc).isoformat()
            }
            supabase.table('overseerr_requests').insert(request_log).execute()
        except Exception as log_error:
            logger.warning(f"Could not log Overseerr request: {log_error}")
        
        return request_result
        
    except HTTPException:
        raise
    except IntegrationException as e:
        logger.error(f"Overseerr request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Overseerr request failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating Overseerr request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create request"
        )
