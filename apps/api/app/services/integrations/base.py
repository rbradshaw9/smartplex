"""
Base class for external service integrations.
Provides common functionality for API clients.
"""

import httpx
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrationException(Exception):
    """Exception raised for integration-related errors."""
    
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        self.service = service
        self.message = message
        self.status_code = status_code
        super().__init__(f"{service}: {message}")


class BaseIntegration(ABC):
    """Base class for all external service integrations."""
    
    def __init__(self, url: str, api_key: str, timeout: int = 30):
        """
        Initialize integration client.
        
        Args:
            url: Base URL for the service API
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the name of the service (e.g., 'Tautulli', 'Sonarr')."""
        pass
    
    @abstractmethod
    def get_health_check_endpoint(self) -> str:
        """Return the endpoint to use for health checks."""
        pass
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the service.
        
        Returns:
            Dict with status and version information
            
        Raises:
            IntegrationException: If connection fails
        """
        try:
            endpoint = self.get_health_check_endpoint()
            response = await self._request('GET', endpoint)
            
            return {
                'status': 'online',
                'service': self.get_service_name(),
                'url': self.url,
                'tested_at': datetime.utcnow().isoformat(),
                'version': response.get('version', 'unknown'),
                'response_time_ms': response.get('_response_time', 0)
            }
            
        except Exception as e:
            logger.error(f"{self.get_service_name()} connection test failed: {e}")
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Connection test failed: {str(e)}"
            )
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the service API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON body
            headers: Additional headers
            
        Returns:
            Response data as dict
            
        Raises:
            IntegrationException: If request fails
        """
        url = f"{self.url}{endpoint}"
        
        # Merge default headers with custom headers
        default_headers = self._get_auth_headers()
        if headers:
            default_headers.update(headers)
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=default_headers
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            response.raise_for_status()
            
            data = response.json() if response.content else {}
            data['_response_time'] = response_time
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"{self.get_service_name()} API error: {e.response.status_code} - {e.response.text}")
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            logger.error(f"{self.get_service_name()} request error: {e}")
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"{self.get_service_name()} unexpected error: {e}")
            raise IntegrationException(
                service=self.get_service_name(),
                message=f"Unexpected error: {str(e)}"
            )
    
    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """Return authentication headers for API requests."""
        pass
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
