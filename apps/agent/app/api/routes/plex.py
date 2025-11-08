"""Plex server integration endpoints."""

from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
import httpx

from app.config import get_settings, AgentSettings

router = APIRouter()


@router.get("/status")
async def get_plex_status(
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Check Plex server status and connectivity."""
    try:
        async with httpx.AsyncClient() as client:
            # Check basic connectivity
            response = await client.get(
                f"{settings.plex_url}/status/sessions",
                timeout=10.0
            )
            
            accessible = response.status_code == 200
            
            status_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "url": settings.plex_url,
                "accessible": accessible,
                "response_code": response.status_code if accessible else None,
            }
            
            if accessible:
                # Get server info if accessible
                try:
                    server_response = await client.get(
                        f"{settings.plex_url}/",
                        params={"X-Plex-Token": settings.plex_token},
                        timeout=5.0
                    )
                    if server_response.status_code == 200:
                        status_info["authenticated"] = True
                        # Parse server XML response for server info (mock for now)
                        status_info["server_info"] = {
                            "version": "1.32.8.7639-fb6452ebf",  # Mock
                            "platform": "Linux",  # Mock
                            "name": "Main Plex Server"  # Mock
                        }
                    else:
                        status_info["authenticated"] = False
                        status_info["auth_error"] = "Invalid token or access denied"
                except Exception as e:
                    status_info["authenticated"] = False
                    status_info["auth_error"] = str(e)
            
            return status_info
            
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "url": settings.plex_url,
            "accessible": False,
            "error": str(e)
        }


@router.get("/libraries")
async def get_plex_libraries(
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Get Plex library information."""
    try:
        # Mock library data - in production, query actual Plex API
        mock_libraries = [
            {
                "id": "1",
                "name": "Movies",
                "type": "movie",
                "item_count": 1247,
                "size_gb": 8456.2,
                "last_scan": "2024-01-01T12:00:00Z"
            },
            {
                "id": "2", 
                "name": "TV Shows",
                "type": "show",
                "item_count": 89,
                "size_gb": 3621.8,
                "last_scan": "2024-01-01T12:30:00Z"
            },
            {
                "id": "3",
                "name": "Music",
                "type": "artist", 
                "item_count": 567,
                "size_gb": 234.5,
                "last_scan": "2023-12-28T15:00:00Z"
            }
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "libraries": mock_libraries,
            "total_libraries": len(mock_libraries),
            "total_items": sum(lib["item_count"] for lib in mock_libraries),
            "total_size_gb": sum(lib["size_gb"] for lib in mock_libraries)
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "libraries": []
        }


@router.post("/scan")
async def trigger_library_scan(
    library_id: str = None,
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Trigger Plex library scan."""
    try:
        # Mock scan trigger - in production, call Plex API
        scan_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "library_id": library_id or "all",
            "scan_triggered": True,
            "message": f"Library scan started for {'all libraries' if not library_id else f'library {library_id}'}",
            "estimated_duration_minutes": 15 if not library_id else 5
        }
        
        return scan_info
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(), 
            "scan_triggered": False,
            "error": str(e)
        }