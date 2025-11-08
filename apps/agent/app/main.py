"""
SmartPlex Local Agent - FastAPI service for Plex server automation.

This agent runs as a Docker container on the same host as your Plex server
and provides:
- Local file system monitoring and cleanup
- Plex library synchronization
- Storage optimization
- Health monitoring and heartbeat reporting
- Local automation without cloud dependencies
"""

import os
import platform
import psutil
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.core.scheduler import setup_scheduled_tasks
from app.api.routes import health, system, plex, cleanup


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Agent lifespan management with background task scheduling."""
    settings = get_settings()
    
    # Startup
    print("🤖 SmartPlex Agent starting up...")
    print(f"🏠 Host: {platform.node()}")
    print(f"🐍 Python: {platform.python_version()}")
    print(f"⚙️ Environment: {settings.environment}")
    
    # Initialize background scheduler
    scheduler = AsyncIOScheduler()
    app.state.scheduler = scheduler
    
    # Setup scheduled tasks (heartbeat, cleanup checks, etc.)
    await setup_scheduled_tasks(scheduler, settings)
    
    # Start scheduler
    scheduler.start()
    print("📅 Background scheduler started")
    
    yield
    
    # Shutdown
    print("🔄 SmartPlex Agent shutting down...")
    scheduler.shutdown(wait=True)
    print("📅 Background scheduler stopped")


# Create FastAPI agent app
app = FastAPI(
    title="SmartPlex Agent",
    description="Local automation agent for Plex servers",
    version="0.1.0",
    docs_url="/docs" if os.getenv("SMARTPLEX_ENV") != "production" else None,
    lifespan=lifespan,
)


@app.exception_handler(404)
async def not_found_handler(request, exc) -> JSONResponse:
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "details": "The requested resource was not found"},
    )


# Include API routes
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(system.router, prefix="/system", tags=["system"])
app.include_router(plex.router, prefix="/plex", tags=["plex"])
app.include_router(cleanup.router, prefix="/cleanup", tags=["cleanup"])


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with agent information."""
    settings = get_settings()
    
    return {
        "service": "SmartPlex Agent",
        "version": "0.1.0",
        "environment": settings.environment,
        "host": platform.node(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "docs": "/docs",
        "status": "🤖 Running",
        "uptime_seconds": psutil.boot_time(),
    }