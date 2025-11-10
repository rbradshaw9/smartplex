"""
Tautulli integration service.
Provides access to enhanced Plex statistics and watch history.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from .base import BaseIntegration, IntegrationException

logger = logging.getLogger(__name__)


class TautulliService(BaseIntegration):
    """Tautulli API client for enhanced Plex statistics."""
    
    def get_service_name(self) -> str:
        return "Tautulli"
    
    def get_health_check_endpoint(self) -> str:
        return "/api/v2"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    async def get_activity(self) -> Dict[str, Any]:
        """
        Get current Plex server activity.
        
        Returns:
            Current streaming activity including active sessions
        """
        response = await self._request(
            'GET',
            '/api/v2',
            params={
                'apikey': self.api_key,
                'cmd': 'get_activity'
            }
        )
        return response.get('response', {}).get('data', {})
    
    async def get_history(
        self,
        user_id: Optional[str] = None,
        length: int = 100,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Get play history from Tautulli.
        
        Args:
            user_id: Filter by specific user (optional)
            length: Number of results to return
            start: Starting offset
            
        Returns:
            Watch history with detailed metadata
        """
        params = {
            'apikey': self.api_key,
            'cmd': 'get_history',
            'length': length,
            'start': start
        }
        
        if user_id:
            params['user_id'] = user_id
        
        response = await self._request('GET', '/api/v2', params=params)
        return response.get('response', {}).get('data', {})
    
    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        Get all Plex libraries.
        
        Returns:
            List of library information
        """
        response = await self._request(
            'GET',
            '/api/v2',
            params={
                'apikey': self.api_key,
                'cmd': 'get_libraries'
            }
        )
        return response.get('response', {}).get('data', [])
    
    async def get_library_media_info(
        self,
        section_id: int,
        length: int = 1000
    ) -> Dict[str, Any]:
        """
        Get media information for a specific library.
        
        Args:
            section_id: Library section ID
            length: Number of results
            
        Returns:
            Media items in the library
        """
        response = await self._request(
            'GET',
            '/api/v2',
            params={
                'apikey': self.api_key,
                'cmd': 'get_library_media_info',
                'section_id': section_id,
                'length': length
            }
        )
        return response.get('response', {}).get('data', {})
    
    async def get_user_watch_time_stats(
        self,
        user_id: Optional[str] = None,
        time_range: int = 30
    ) -> Dict[str, Any]:
        """
        Get watch time statistics for a user.
        
        Args:
            user_id: User ID (optional, defaults to all users)
            time_range: Number of days to include
            
        Returns:
            Watch time statistics
        """
        response = await self._request(
            'GET',
            '/api/v2',
            params={
                'apikey': self.api_key,
                'cmd': 'get_user_watch_time_stats',
                'user_id': user_id or '',
                'time_range': time_range
            }
        )
        return response.get('response', {}).get('data', [])
    
    async def get_plays_by_date(
        self,
        time_range: int = 30,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get play counts grouped by date.
        
        Args:
            time_range: Number of days to include
            user_id: Filter by user (optional)
            
        Returns:
            Play counts by date
        """
        params = {
            'apikey': self.api_key,
            'cmd': 'get_plays_by_date',
            'time_range': time_range
        }
        
        if user_id:
            params['user_id'] = user_id
        
        response = await self._request('GET', '/api/v2', params=params)
        return response.get('response', {}).get('data', {})
    
    async def get_stream_type_by_top_10_platforms(
        self,
        time_range: int = 30
    ) -> Dict[str, Any]:
        """
        Get streaming statistics by platform.
        
        Args:
            time_range: Number of days to analyze
            
        Returns:
            Stream type statistics by platform
        """
        response = await self._request(
            'GET',
            '/api/v2',
            params={
                'apikey': self.api_key,
                'cmd': 'get_stream_type_by_top_10_platforms',
                'time_range': time_range
            }
        )
        return response.get('response', {}).get('data', {})
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and get server info."""
        try:
            response = await self._request(
                'GET',
                '/api/v2',
                params={
                    'apikey': self.api_key,
                    'cmd': 'status'
                }
            )
            
            result = response.get('response', {}).get('result', 'error')
            
            if result == 'success':
                return {
                    'status': 'online',
                    'service': self.get_service_name(),
                    'url': self.url,
                    'tested_at': datetime.utcnow().isoformat(),
                    'version': 'connected',
                    'response_time_ms': response.get('_response_time', 0)
                }
            else:
                raise IntegrationException(
                    service=self.get_service_name(),
                    message="API returned error status"
                )
                
        except Exception as e:
            logger.error(f"Tautulli connection test failed: {e}")
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Connection test failed: {str(e)}"
            )
