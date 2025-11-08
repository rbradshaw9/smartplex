"""
Background task scheduler for SmartPlex Agent.
Manages automated cleanup, heartbeat reporting, and monitoring tasks.
"""

import asyncio
import httpx
import psutil
from datetime import datetime
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import AgentSettings


async def setup_scheduled_tasks(scheduler: AsyncIOScheduler, settings: AgentSettings) -> None:
    """
    Setup all background tasks for the SmartPlex Agent.
    
    Args:
        scheduler: AsyncIO scheduler instance
        settings: Agent configuration settings
    """
    # Heartbeat task - report agent status to SmartPlex API
    scheduler.add_job(
        send_heartbeat,
        "interval",
        seconds=settings.heartbeat_interval,
        args=[settings],
        id="heartbeat",
        replace_existing=True,
    )
    
    # Storage monitoring task
    scheduler.add_job(
        check_storage_usage,
        "cron",
        hour="*/6",  # Every 6 hours
        args=[settings],
        id="storage_check",
        replace_existing=True,
    )
    
    # Cleanup analysis task (only if enabled)
    if settings.cleanup_enabled:
        scheduler.add_job(
            analyze_cleanup_candidates,
            "cron", 
            hour=2,  # Daily at 2 AM
            args=[settings],
            id="cleanup_analysis",
            replace_existing=True,
        )
    
    print(f"📅 Scheduled {len(scheduler.get_jobs())} background tasks")


async def send_heartbeat(settings: AgentSettings) -> None:
    """Send heartbeat with system status to SmartPlex API."""
    try:
        # Gather system metrics
        system_info = {
            "agent_id": settings.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": get_disk_usage_info(settings.plex_library_paths),
                "uptime_seconds": psutil.boot_time(),
            },
            "plex": {
                "url": settings.plex_url,
                "accessible": await check_plex_accessibility(settings.plex_url),
            }
        }
        
        # Send to SmartPlex API (if configured)
        if settings.smartplex_api_url and settings.smartplex_api_token:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.smartplex_api_url}/agents/heartbeat",
                    json=system_info,
                    headers={"Authorization": f"Bearer {settings.smartplex_api_token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    print(f"💓 Heartbeat sent successfully")
                else:
                    print(f"⚠️ Heartbeat failed: {response.status_code}")
        else:
            print(f"💓 Heartbeat (local): CPU {system_info['system']['cpu_percent']:.1f}%, Memory {system_info['system']['memory_percent']:.1f}%")
            
    except Exception as e:
        print(f"❌ Heartbeat error: {str(e)}")


async def check_storage_usage(settings: AgentSettings) -> None:
    """Monitor storage usage and alert if thresholds are exceeded."""
    try:
        disk_info = get_disk_usage_info(settings.plex_library_paths)
        
        for path, usage in disk_info.items():
            percent_used = usage["percent_used"]
            
            if percent_used >= settings.storage_threshold_critical:
                print(f"🚨 CRITICAL: Storage usage at {percent_used:.1f}% for {path}")
                await send_storage_alert(settings, path, percent_used, "critical")
                
            elif percent_used >= settings.storage_threshold_warning:
                print(f"⚠️ WARNING: Storage usage at {percent_used:.1f}% for {path}")
                await send_storage_alert(settings, path, percent_used, "warning")
            else:
                print(f"✅ Storage OK: {percent_used:.1f}% used for {path}")
                
    except Exception as e:
        print(f"❌ Storage check error: {str(e)}")


async def analyze_cleanup_candidates(settings: AgentSettings) -> None:
    """Analyze media files that could be candidates for cleanup."""
    try:
        print("🧹 Starting cleanup analysis...")
        
        # Mock cleanup analysis - in production, scan actual files
        cleanup_candidates = {
            "old_movies": [
                {"path": "/data/movies/old_movie_2019.mkv", "size_gb": 8.5, "last_accessed": "2023-06-15"},
                {"path": "/data/movies/unwatched_2020.mp4", "size_gb": 12.3, "last_accessed": "2023-08-22"},
            ],
            "duplicate_files": [],
            "corrupted_files": [],
            "total_space_recoverable_gb": 20.8,
        }
        
        if settings.cleanup_dry_run:
            print(f"🔍 DRY RUN: Found {cleanup_candidates['total_space_recoverable_gb']:.1f}GB of cleanup candidates")
        else:
            print(f"🧹 CLEANUP: Processing {cleanup_candidates['total_space_recoverable_gb']:.1f}GB of files")
            
        # Send results to SmartPlex API
        await send_cleanup_report(settings, cleanup_candidates)
        
    except Exception as e:
        print(f"❌ Cleanup analysis error: {str(e)}")


def get_disk_usage_info(paths: list[str]) -> Dict[str, Dict[str, Any]]:
    """Get disk usage information for specified paths."""
    usage_info = {}
    
    for path in paths:
        try:
            usage = psutil.disk_usage(path)
            usage_info[path] = {
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "percent_used": (usage.used / usage.total) * 100,
            }
        except Exception as e:
            usage_info[path] = {"error": str(e)}
            
    return usage_info


async def check_plex_accessibility(plex_url: str) -> bool:
    """Check if Plex server is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{plex_url}/status/sessions", timeout=5.0)
            return response.status_code == 200
    except Exception:
        return False


async def send_storage_alert(settings: AgentSettings, path: str, usage_percent: float, level: str) -> None:
    """Send storage alert to SmartPlex API."""
    if not settings.smartplex_api_url or not settings.smartplex_api_token:
        return
        
    try:
        alert_data = {
            "agent_id": settings.agent_id,
            "type": "storage_alert",
            "level": level,
            "path": path,
            "usage_percent": usage_percent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.smartplex_api_url}/agents/alerts",
                json=alert_data,
                headers={"Authorization": f"Bearer {settings.smartplex_api_token}"},
                timeout=10.0
            )
    except Exception as e:
        print(f"❌ Failed to send storage alert: {str(e)}")


async def send_cleanup_report(settings: AgentSettings, cleanup_data: Dict[str, Any]) -> None:
    """Send cleanup analysis report to SmartPlex API."""
    if not settings.smartplex_api_url or not settings.smartplex_api_token:
        return
        
    try:
        report_data = {
            "agent_id": settings.agent_id,
            "type": "cleanup_report",
            "data": cleanup_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.smartplex_api_url}/agents/reports",
                json=report_data,
                headers={"Authorization": f"Bearer {settings.smartplex_api_token}"},
                timeout=10.0
            )
    except Exception as e:
        print(f"❌ Failed to send cleanup report: {str(e)}")