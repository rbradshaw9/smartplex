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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import get_settings
from app.api.routes import health, sync, ai, plex_auth, plex, plex_sync, integrations, admin_deletion, admin_tautulli, webhooks, system_config, feedback
from app.core.supabase import get_supabase_client
from app.core.exceptions import SmartPlexException
from app.core.logging import setup_logging, get_logger
import logging

# Setup logging
logger = get_logger("main")

# Initialize Sentry for error tracking
settings = get_settings()
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn or "https://9352877a711f16edf148d59fd3d7900b@o4510303274926080.ingest.us.sentry.io/4510346730733568",
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
        ],
        traces_sample_rate=1.0,  # Adjust in production
        environment=settings.environment,
        send_default_pii=True,  # Capture request headers and IP for debugging
        before_send=lambda event, hint: event if settings.sentry_dsn else None,
    )
    logger.info("🔔 Sentry error tracking initialized")

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
    "https://smartplex-ecru.vercel.app",  # Production frontend
]

# Add production origins from environment
if settings.environment == "production":
    frontend_url = os.getenv("FRONTEND_URL", "https://smartplex-ecru.vercel.app")
    if frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

logger.info(f"🔒 CORS allowed origins: {allowed_origins}")

# Allow all Vercel preview deployments using regex
allow_origin_regex = r"https://.*\.vercel\.app"


# Middleware to trust proxy headers (for Railway HTTPS termination)
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Trust X-Forwarded-Proto header from Railway's load balancer
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto == "https":
            # Mark request as secure
            request.scope["scheme"] = "https"
        return await call_next(request)


app.add_middleware(ProxyHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
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
app.include_router(plex_sync.router, prefix="/api/plex", tags=["plex", "sync"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(feedback.router, tags=["feedback"])
app.include_router(admin_deletion.router, prefix="/api/admin/deletion", tags=["admin", "deletion"])
app.include_router(admin_tautulli.router, prefix="/api/admin", tags=["admin", "tautulli"])
app.include_router(system_config.router, prefix="/api/admin/system", tags=["admin", "system"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "SmartPlex API",
        "version": "0.1.0", 
        "docs": "/docs",
        "status": "🚀 Running",
    }


@app.get("/sentry-debug")
async def trigger_error():
    """Sentry debug endpoint to verify error tracking is working."""
    division_by_zero = 1 / 0
    return division_by_zero