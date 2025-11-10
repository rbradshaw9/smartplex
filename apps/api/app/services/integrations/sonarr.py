"""
Sonarr integration service.
Provides access to TV show management and monitoring.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import BaseIntegration, IntegrationException

logger = logging.getLogger(__name__)


class SonarrService(BaseIntegration):
    """Sonarr API client for TV show management."""
    
    def get_service_name(self) -> str:
        return "Sonarr"
    
    def get_health_check_endpoint(self) -> str:
        return "/api/v3/system/status"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            'X-Api-Key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    async def get_series(self) -> List[Dict[str, Any]]:
        """
        Get all series in Sonarr.
        
        Returns:
            List of series with metadata
        """
        return await self._request('GET', '/api/v3/series')
    
    async def get_series_by_id(self, series_id: int) -> Dict[str, Any]:
        """
        Get specific series by ID.
        
        Args:
            series_id: Sonarr series ID
            
        Returns:
            Series details
        """
        return await self._request('GET', f'/api/v3/series/{series_id}')
    
    async def search_series(self, term: str) -> List[Dict[str, Any]]:
        """
        Search for series by name.
        
        Args:
            term: Search term
            
        Returns:
            List of matching series
        """
        return await self._request(
            'GET',
            '/api/v3/series/lookup',
            params={'term': term}
        )
    
    async def add_series(
        self,
        tvdb_id: int,
        quality_profile_id: int,
        root_folder_path: str,
        monitored: bool = True,
        season_folder: bool = True,
        search_for_missing: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new series to Sonarr.
        
        Args:
            tvdb_id: TVDB ID of the series
            quality_profile_id: Quality profile ID
            root_folder_path: Root folder path for the series
            monitored: Whether to monitor the series
            season_folder: Use season folders
            search_for_missing: Search for missing episodes after adding
            
        Returns:
            Added series information
        """
        # First, lookup the series details
        series_list = await self.search_series(f"tvdb:{tvdb_id}")
        
        if not series_list:
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Series with TVDB ID {tvdb_id} not found"
            )
        
        series_data = series_list[0]
        
        # Prepare the payload
        payload = {
            'tvdbId': tvdb_id,
            'title': series_data.get('title'),
            'qualityProfileId': quality_profile_id,
            'titleSlug': series_data.get('titleSlug'),
            'images': series_data.get('images', []),
            'seasons': series_data.get('seasons', []),
            'rootFolderPath': root_folder_path,
            'monitored': monitored,
            'seasonFolder': season_folder,
            'addOptions': {
                'searchForMissingEpisodes': search_for_missing
            }
        }
        
        return await self._request('POST', '/api/v3/series', json=payload)
    
    async def get_queue(self) -> Dict[str, Any]:
        """
        Get download queue.
        
        Returns:
            Current download queue with status
        """
        return await self._request('GET', '/api/v3/queue')
    
    async def get_calendar(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming episodes calendar.
        
        Args:
            start_date: Start date for calendar (optional)
            end_date: End date for calendar (optional)
            
        Returns:
            List of upcoming episodes
        """
        params = {}
        if start_date:
            params['start'] = start_date.isoformat()
        if end_date:
            params['end'] = end_date.isoformat()
        
        return await self._request('GET', '/api/v3/calendar', params=params)
    
    async def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """
        Get available quality profiles.
        
        Returns:
            List of quality profiles
        """
        return await self._request('GET', '/api/v3/qualityprofile')
    
    async def get_root_folders(self) -> List[Dict[str, Any]]:
        """
        Get configured root folders.
        
        Returns:
            List of root folder paths
        """
        return await self._request('GET', '/api/v3/rootfolder')
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status and version information.
        
        Returns:
            System status details
        """
        return await self._request('GET', '/api/v3/system/status')
    
    async def delete_series(self, series_id: int, delete_files: bool = False) -> None:
        """
        Delete a series from Sonarr.
        
        Args:
            series_id: Series ID to delete
            delete_files: Whether to delete files from disk
        """
        params = {'deleteFiles': str(delete_files).lower()}
        await self._request('DELETE', f'/api/v3/series/{series_id}', params=params)
