"""
Radarr integration service.
Provides access to movie management and monitoring.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import BaseIntegration, IntegrationException

logger = logging.getLogger(__name__)


class RadarrService(BaseIntegration):
    """Radarr API client for movie management."""
    
    def get_service_name(self) -> str:
        return "Radarr"
    
    def get_health_check_endpoint(self) -> str:
        return "/api/v3/system/status"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            'X-Api-Key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    async def get_movies(self) -> List[Dict[str, Any]]:
        """
        Get all movies in Radarr.
        
        Returns:
            List of movies with metadata
        """
        return await self._request('GET', '/api/v3/movie')  # type: ignore
    
    async def get_movie_by_id(self, movie_id: int) -> Dict[str, Any]:
        """
        Get specific movie by ID.
        
        Args:
            movie_id: Radarr movie ID
            
        Returns:
            Movie details
        """
        return await self._request('GET', f'/api/v3/movie/{movie_id}')
    
    async def search_movies(self, term: str) -> List[Dict[str, Any]]:
        """
        Search for movies by title.
        
        Args:
            term: Search term
            
        Returns:
            List of matching movies
        """
        return await self._request(  # type: ignore
            'GET',
            '/api/v3/movie/lookup',
            params={'term': term}
        )
    
    async def add_movie(
        self,
        tmdb_id: int,
        quality_profile_id: int,
        root_folder_path: str,
        monitored: bool = True,
        search_for_movie: bool = False,
        minimum_availability: str = "announced"
    ) -> Dict[str, Any]:
        """
        Add a new movie to Radarr.
        
        Args:
            tmdb_id: TMDB ID of the movie
            quality_profile_id: Quality profile ID
            root_folder_path: Root folder path for the movie
            monitored: Whether to monitor the movie
            search_for_movie: Search for movie after adding
            minimum_availability: Minimum availability (announced, inCinemas, released)
            
        Returns:
            Added movie information
        """
        # First, lookup the movie details
        movies = await self.search_movies(f"tmdb:{tmdb_id}")
        
        if not movies:
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Movie with TMDB ID {tmdb_id} not found"
            )
        
        movie_data = movies[0]
        
        # Prepare the payload
        payload = {
            'tmdbId': tmdb_id,
            'title': movie_data.get('title'),
            'qualityProfileId': quality_profile_id,
            'titleSlug': movie_data.get('titleSlug'),
            'images': movie_data.get('images', []),
            'year': movie_data.get('year'),
            'rootFolderPath': root_folder_path,
            'monitored': monitored,
            'minimumAvailability': minimum_availability,
            'addOptions': {
                'searchForMovie': search_for_movie
            }
        }
        
        return await self._request('POST', '/api/v3/movie', json=payload)
    
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
        Get upcoming movie releases.
        
        Args:
            start_date: Start date for calendar (optional)
            end_date: End date for calendar (optional)
            
        Returns:
            List of upcoming movie releases
        """
        params = {}
        if start_date:
            params['start'] = start_date.isoformat()
        if end_date:
            params['end'] = end_date.isoformat()
        
        return await self._request('GET', '/api/v3/calendar', params=params)  # type: ignore
    
    async def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """
        Get available quality profiles.
        
        Returns:
            List of quality profiles
        """
        return await self._request('GET', '/api/v3/qualityprofile')  # type: ignore
    
    async def get_root_folders(self) -> List[Dict[str, Any]]:
        """
        Get configured root folders.
        
        Returns:
            List of root folder paths
        """
        return await self._request('GET', '/api/v3/rootfolder')  # type: ignore
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status and version information.
        
        Returns:
            System status details
        """
        return await self._request('GET', '/api/v3/system/status')
    
    async def delete_movie(self, movie_id: int, delete_files: bool = False) -> None:
        """
        Delete a movie from Radarr.
        
        Args:
            movie_id: Movie ID to delete
            delete_files: Whether to delete files from disk
        """
        params = {'deleteFiles': str(delete_files).lower()}
        await self._request('DELETE', f'/api/v3/movie/{movie_id}', params=params)
    
    async def get_missing_movies(self) -> List[Dict[str, Any]]:
        """
        Get movies that are monitored but missing from disk.
        
        Returns:
            List of missing movies
        """
        return await self._request('GET', '/api/v3/wanted/missing')  # type: ignore
