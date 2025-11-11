"""
Health check endpoints for SmartPlex API.
Used by load balancers and monitoring systems to check service health.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.supabase import get_supabase_client
from app.config import get_settings, Settings

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "smartplex-api",
        "version": "0.1.0",
    }


@router.get("/detailed")
async def detailed_health_check(
    settings: Settings = Depends(get_settings),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Detailed health check with dependency status.
    Tests connections to Supabase and other external services.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "smartplex-api", 
        "version": "0.1.0",
        "environment": settings.environment,
        "checks": {},
    }
    
    # Test Supabase connection
    try:
        # Simple query to test database connection
        response = supabase.table("users").select("id").limit(1).execute()
        health_status["checks"]["supabase"] = {
            "status": "healthy",
            "response_time_ms": 50,  # Placeholder
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["supabase"] = {
            "status": "unhealthy", 
            "error": str(e),
            "message": "Database connection failed"
        }
        health_status["status"] = "degraded"
    
    # Test AI service availability
    ai_status = "healthy" if settings.openai_api_key or settings.anthropic_api_key else "unavailable"
    health_status["checks"]["ai_services"] = {
        "status": ai_status,
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
    }
    
    # Test Redis connection (optional)
    health_status["checks"]["redis"] = {
        "status": "not_implemented",
        "message": "Redis health check not yet implemented"
    }
    
    return health_status


@router.get("/ready")
async def readiness_check(
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, str]:
    """
    Kubernetes/Docker readiness probe.
    Returns 200 only if service is ready to accept traffic.
    """
    try:
        # Test critical dependencies
        supabase.table("users").select("id").limit(1).execute()
        return {"status": "ready"}
    except Exception:
        # Return 503 if not ready
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/stats")
async def system_stats(
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get system statistics and database counts.
    Useful for admin dashboards and monitoring.
    """
    try:
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "counts": {},
            "recent_activity": {}
        }
        
        # Get counts for main tables
        tables = ['users', 'servers', 'media_items', 'deletion_events', 'sync_events']
        for table in tables:
            try:
                result = supabase.table(table).select('id', count='exact').limit(1).execute()
                stats["counts"][table] = result.count if hasattr(result, 'count') else 0
            except:
                stats["counts"][table] = 0
        
        # Get most recent sync
        try:
            recent_sync = supabase.table('sync_events')\
                .select('*')\
                .order('started_at', desc=True)\
                .limit(1)\
                .execute()
            if recent_sync.data:
                stats["recent_activity"]["last_sync"] = recent_sync.data[0]
        except:
            pass
        
        # Get storage usage
        try:
            storage_result = supabase.table('media_items')\
                .select('file_size_mb')\
                .not_.is_('file_size_mb', 'null')\
                .execute()
            if storage_result.data:
                total_mb = sum(item.get('file_size_mb', 0) or 0 for item in storage_result.data)
                stats["storage"] = {
                    "total_mb": total_mb,
                    "total_gb": round(total_mb / 1024, 2),
                    "total_tb": round(total_mb / (1024 * 1024), 2)
                }
        except:
            pass
        
        return stats
    except Exception as e:
        return {
            "error": "Failed to retrieve system statistics",
            "details": str(e)
        }