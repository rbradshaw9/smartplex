"""System monitoring and metrics endpoints."""

from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
import psutil
import platform

from app.config import get_settings, AgentSettings

router = APIRouter()


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "platform": platform.system(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
            },
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "percent": memory.percent,
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
            "uptime_seconds": psutil.boot_time(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


@router.get("/storage")
async def get_storage_info(
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Get storage information for Plex library paths."""
    storage_info = {
        "timestamp": datetime.utcnow().isoformat(),
        "paths": {}
    }
    
    for path in settings.plex_library_paths:
        try:
            usage = psutil.disk_usage(path)
            storage_info["paths"][path] = {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "percent_used": (usage.used / usage.total) * 100,
                "status": "normal",
            }
            
            # Add status warnings
            percent_used = (usage.used / usage.total) * 100
            if percent_used >= settings.storage_threshold_critical:
                storage_info["paths"][path]["status"] = "critical"
            elif percent_used >= settings.storage_threshold_warning:
                storage_info["paths"][path]["status"] = "warning"
                
        except Exception as e:
            storage_info["paths"][path] = {
                "error": str(e),
                "status": "error"
            }
    
    return storage_info


@router.get("/processes")
async def get_process_info() -> Dict[str, Any]:
    """Get information about running processes."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                # Only include processes using significant resources
                if pinfo['cpu_percent'] > 1.0 or pinfo['memory_percent'] > 1.0:
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "process_count": len(psutil.pids()),
            "top_processes": processes[:10],  # Top 10 processes
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}