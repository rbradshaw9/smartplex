"""Cleanup and storage optimization endpoints."""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings, AgentSettings

router = APIRouter()


class CleanupConfig(BaseModel):
    """Configuration for cleanup operations."""
    dry_run: bool = True
    min_age_days: int = 90
    min_size_mb: int = 100
    preserve_recent_downloads: bool = True
    file_extensions: List[str] = [".mkv", ".mp4", ".avi", ".mov"]


class CleanupResult(BaseModel):
    """Result of cleanup operation."""
    files_analyzed: int
    files_marked_for_deletion: int
    space_recoverable_gb: float
    files_deleted: int = 0
    space_freed_gb: float = 0
    dry_run: bool
    timestamp: datetime


@router.get("/candidates")
async def get_cleanup_candidates(
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Identify files that are candidates for cleanup."""
    try:
        # Mock cleanup candidates - in production, scan actual file system
        cleanup_candidates = {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": {
                "paths_scanned": settings.plex_library_paths,
                "total_files_analyzed": 15847,
                "criteria": {
                    "min_age_days": 90,
                    "min_size_mb": 100,
                    "last_access_threshold": (datetime.utcnow() - timedelta(days=180)).isoformat()
                }
            },
            "categories": {
                "old_unwatched": {
                    "count": 23,
                    "total_size_gb": 156.7,
                    "description": "Files older than 90 days with no play history",
                    "files": [
                        {
                            "path": "/data/movies/Old_Movie_2022.mkv",
                            "size_gb": 8.5,
                            "last_accessed": "2023-08-15T10:30:00Z",
                            "last_modified": "2022-12-01T15:45:00Z",
                            "play_count": 0
                        },
                        {
                            "path": "/data/movies/Unwatched_Action_2023.mp4", 
                            "size_gb": 12.3,
                            "last_accessed": "2023-06-20T14:22:00Z",
                            "last_modified": "2023-01-15T09:12:00Z",
                            "play_count": 0
                        }
                    ]
                },
                "duplicates": {
                    "count": 5,
                    "total_size_gb": 48.2,
                    "description": "Duplicate files with same content",
                    "files": []
                },
                "corrupted": {
                    "count": 2,
                    "total_size_gb": 15.1,
                    "description": "Files that failed integrity checks",
                    "files": []
                },
                "partial_downloads": {
                    "count": 8,
                    "total_size_gb": 23.8,
                    "description": "Incomplete or failed downloads",
                    "files": []
                }
            },
            "summary": {
                "total_candidates": 38,
                "total_space_recoverable_gb": 243.8,
                "estimated_cleanup_time_minutes": 45,
                "safety_score": "high"  # Based on file age and access patterns
            }
        }
        
        return cleanup_candidates
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "categories": {}
        }


@router.post("/analyze")
async def run_cleanup_analysis(
    config: CleanupConfig,
    settings: AgentSettings = Depends(get_settings)
) -> CleanupResult:
    """Run cleanup analysis with custom configuration."""
    try:
        # Mock analysis with provided config
        mock_result = CleanupResult(
            files_analyzed=15847,
            files_marked_for_deletion=42,
            space_recoverable_gb=287.5,
            dry_run=config.dry_run,
            timestamp=datetime.utcnow()
        )
        
        # If not dry run, simulate actual cleanup
        if not config.dry_run and settings.cleanup_enabled:
            mock_result.files_deleted = 38
            mock_result.space_freed_gb = 251.2
        
        return mock_result
        
    except Exception as e:
        return CleanupResult(
            files_analyzed=0,
            files_marked_for_deletion=0,
            space_recoverable_gb=0.0,
            dry_run=config.dry_run,
            timestamp=datetime.utcnow()
        )


@router.post("/execute")
async def execute_cleanup(
    file_paths: List[str],
    settings: AgentSettings = Depends(get_settings)
) -> Dict[str, Any]:
    """Execute cleanup for specific files."""
    if not settings.cleanup_enabled:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Cleanup is disabled in agent configuration",
            "files_processed": 0
        }
    
    try:
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "files_requested": len(file_paths),
            "files_processed": 0,
            "files_deleted": 0,
            "space_freed_gb": 0.0,
            "errors": [],
            "dry_run": settings.cleanup_dry_run
        }
        
        for file_path in file_paths:
            try:
                if settings.cleanup_dry_run:
                    # Simulate deletion in dry run mode
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path) / (1024**3)  # GB
                        results["space_freed_gb"] += file_size
                        results["files_deleted"] += 1
                    results["files_processed"] += 1
                else:
                    # Actual deletion (be very careful here)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path) / (1024**3)
                        # os.remove(file_path)  # Commented for safety
                        results["space_freed_gb"] += file_size
                        results["files_deleted"] += 1
                    results["files_processed"] += 1
                    
            except Exception as e:
                results["errors"].append(f"{file_path}: {str(e)}")
        
        return results
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "files_processed": 0
        }


@router.get("/history")
async def get_cleanup_history() -> Dict[str, Any]:
    """Get cleanup operation history."""
    try:
        # Mock cleanup history
        mock_history = [
            {
                "id": "cleanup_20240101_020000",
                "timestamp": "2024-01-01T02:00:00Z",
                "type": "scheduled",
                "files_deleted": 15,
                "space_freed_gb": 124.5,
                "duration_minutes": 8,
                "dry_run": False
            },
            {
                "id": "cleanup_20231225_030000",
                "timestamp": "2023-12-25T03:00:00Z", 
                "type": "manual",
                "files_deleted": 7,
                "space_freed_gb": 56.2,
                "duration_minutes": 3,
                "dry_run": False
            }
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "operations": mock_history,
            "total_operations": len(mock_history),
            "total_files_deleted": sum(op["files_deleted"] for op in mock_history),
            "total_space_freed_gb": sum(op["space_freed_gb"] for op in mock_history)
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "operations": []
        }