"""
SmartPlex FastAPI Backend Application

This is the main FastAPI application for SmartPlex, providing:
- REST API endpoints for web frontend
- AI/LLM integration for chat and recommendations  
- Supabase database integration
- Plex server synchronization
- Background job processing
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.routes import health, sync, ai, plex_auth, plex
from app.core.supabase import get_supabase_client
from app.core.exceptions import SmartPlexException
from app.core.logging import setup_logging, get_logger
import logging

# Setup logging
logger = get_logger("main")

# Suppress noisy PlexAPI connection logs
logging.getLogger("plexapi").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    settings = get_settings()
    
    # Setup logging with environment-based level
    log_level = "DEBUG" if settings.environment == "development" else "INFO"
    setup_logging(log_level)
    
    logger.info("🚀 SmartPlex API starting up...")
    logger.info(f"🔧 Environment: {settings.environment}")
    logger.info(f"🔗 Supabase URL: {settings.supabase_url}")
    logger.info(f"🔑 Supabase Service Key: {'SET' if settings.supabase_service_key else 'MISSING'}")
    logger.info(f"🌐 Frontend URL: {settings.frontend_url}")
    
    yield
    
    # Shutdown
    logger.info("🔄 SmartPlex API shutting down...")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="SmartPlex API",
    description="The autonomous, AI-powered Plex server ecosystem backend",
    version="0.1.0",
    docs_url="/docs" if os.getenv("SMARTPLEX_ENV") != "production" else None,
    redoc_url="/redoc" if os.getenv("SMARTPLEX_ENV") != "production" else None,
    lifespan=lifespan,
)

# CORS middleware for frontend integration
settings = get_settings()
allowed_origins = [
    "http://localhost:3000",  # Next.js dev
]

# Add production origins from environment
if settings.environment == "production":
    frontend_url = os.getenv("FRONTEND_URL", "https://smartplex-ecru.vercel.app")
    allowed_origins.append(frontend_url)
    allowed_origins.append("https://*.vercel.app")  # Vercel preview deployments
else:
    # Development: allow all Vercel preview URLs
    allowed_origins.extend([
        "https://smartplex-ecru.vercel.app",
        "https://*.vercel.app",
    ])

logger.info(f"🔒 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SmartPlexException)
async def smartplex_exception_handler(request, exc: SmartPlexException) -> JSONResponse:
    """Handle custom SmartPlex exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
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
app.include_router(sync.router, prefix="/sync", tags=["sync"])  
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(plex_auth.router, prefix="/api/auth/plex", tags=["authentication"])
app.include_router(plex.router, prefix="/api", tags=["plex"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "SmartPlex API",
        "version": "0.1.0", 
        "docs": "/docs",
        "status": "🚀 Running",
    }