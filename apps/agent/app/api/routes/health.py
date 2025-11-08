"""Agent health check endpoints."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
import psutil

from app.config import get_settings, AgentSettings

router = APIRouter()


@router.get("/")
async def agent_health_check() -> Dict[str, Any]:
    """Basic agent health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "smartplex-agent",
        "version": "0.1.0",
    }


@router.get("/detailed")
async def detailed_health_check(
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Detailed health check with system metrics."""
    try:
        # System metrics
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "smartplex-agent",
            "version": "0.1.0",
            "agent_id": settings.agent_id,
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk_usage.total / (1024**3),
                    "free_gb": disk_usage.free / (1024**3),
                    "percent": (disk_usage.used / disk_usage.total) * 100
                }
            },
            "plex": {
                "url": settings.plex_url,
                "configured": bool(settings.plex_token)
            },
            "cleanup": {
                "enabled": settings.cleanup_enabled,
                "dry_run": settings.cleanup_dry_run
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }