"""
Overseerr integration service.
Provides access to media request management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import BaseIntegration, IntegrationException

logger = logging.getLogger(__name__)


class OverseerrService(BaseIntegration):
    """Overseerr API client for media request management."""
    
    def get_service_name(self) -> str:
        return "Overseerr"
    
    def get_health_check_endpoint(self) -> str:
        return "/api/v1/status"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            'X-Api-Key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    async def get_requests(
        self,
        take: int = 20,
        skip: int = 0,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get media requests.
        
        Args:
            take: Number of results to return
            skip: Number of results to skip
            status: Filter by status (pending, approved, declined, available)
            
        Returns:
            Paginated request list
        """
        params = {'take': take, 'skip': skip}
        if status:
            params['filter'] = status
        
        return await self._request('GET', '/api/v1/request', params=params)
    
    async def get_request_by_id(self, request_id: int) -> Dict[str, Any]:
        """
        Get specific request by ID.
        
        Args:
            request_id: Request ID
            
        Returns:
            Request details
        """
        return await self._request('GET', f'/api/v1/request/{request_id}')
    
    async def create_request(
        self,
        media_type: str,
        media_id: int,
        seasons: Optional[List[int]] = None,
        is_4k: bool = False,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new media request.
        
        Args:
            media_type: Type of media ('movie' or 'tv')
            media_id: TMDB ID of the media
            seasons: List of season numbers (for TV shows)
            is_4k: Whether to request 4K quality
            user_id: Overseerr user ID to attribute the request to (optional)
            
        Returns:
            Created request information
        """
        payload = {
            'mediaType': media_type,
            'mediaId': media_id,
            'is4k': is_4k
        }
        
        if media_type == 'tv' and seasons:
            payload['seasons'] = seasons
            
        if user_id is not None:
            payload['userId'] = user_id
        
        return await self._request('POST', '/api/v1/request', json=payload)
    
    async def approve_request(
        self,
        request_id: int,
        is_4k: bool = False
    ) -> Dict[str, Any]:
        """
        Approve a pending request.
        
        Args:
            request_id: Request ID to approve
            is_4k: Whether this is a 4K request
            
        Returns:
            Updated request information
        """
        endpoint = f'/api/v1/request/{request_id}/{"4k" if is_4k else ""}approve'
        return await self._request('POST', endpoint.replace('//', '/'))
    
    async def decline_request(
        self,
        request_id: int,
        is_4k: bool = False
    ) -> Dict[str, Any]:
        """
        Decline a pending request.
        
        Args:
            request_id: Request ID to decline
            is_4k: Whether this is a 4K request
            
        Returns:
            Updated request information
        """
        endpoint = f'/api/v1/request/{request_id}/{"4k" if is_4k else ""}decline'
        return await self._request('POST', endpoint.replace('//', '/'))
    
    async def delete_request(self, request_id: int) -> None:
        """
        Delete a request.
        
        Args:
            request_id: Request ID to delete
        """
        await self._request('DELETE', f'/api/v1/request/{request_id}')
    
    async def search_media(
        self,
        query: str,
        page: int = 1,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Search for media in TMDB.
        
        Args:
            query: Search query
            page: Page number
            language: Language code
            
        Returns:
            Search results from TMDB
        """
        params = {
            'query': query,
            'page': page,
            'language': language
        }
        return await self._request('GET', '/api/v1/search', params=params)
    
    async def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        Get movie details from TMDB.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Movie details
        """
        return await self._request('GET', f'/api/v1/movie/{tmdb_id}')
    
    async def get_tv_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        Get TV show details from TMDB.
        
        Args:
            tmdb_id: TMDB TV show ID
            
        Returns:
            TV show details
        """
        return await self._request('GET', f'/api/v1/tv/{tmdb_id}')
    
    async def get_users(self) -> Dict[str, Any]:
        """
        Get all Overseerr users.
        
        Returns:
            List of users
        """
        return await self._request('GET', '/api/v1/user')
    
    async def get_user_requests(self, user_id: int) -> Dict[str, Any]:
        """
        Get requests made by a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            User's requests
        """
        return await self._request('GET', f'/api/v1/user/{user_id}/requests')
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get Overseerr status and configuration.
        
        Returns:
            Status information
        """
        return await self._request('GET', '/api/v1/status')
    
    async def get_settings(self) -> Dict[str, Any]:
        """
        Get Overseerr settings.
        
        Returns:
            Settings configuration
        """
        return await self._request('GET', '/api/v1/settings/main')
