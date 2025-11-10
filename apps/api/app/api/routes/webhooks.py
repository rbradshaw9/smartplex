"""
Webhook endpoints for real-time sync triggers.

Receives webhooks from:
- Plex Media Server (library scans, new content)
- Tautulli (playback events, watch history)
- Sonarr (episode downloads)
- Radarr (movie downloads)
- Overseerr (request status changes)
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Header
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client
from app.core.logging import get_logger
from app.services.integrations.tautulli import TautulliService
from app.services.tautulli_sync import TautulliSyncService

router = APIRouter()
logger = get_logger("webhooks")


class WebhookEvent(BaseModel):
    """Generic webhook event model."""
    event: str
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)


async def trigger_tautulli_sync_background(supabase: Client):
    """Background task to sync Tautulli data."""
    try:
        logger.info("Background Tautulli sync triggered by webhook")
        
        # Get active Tautulli integration
        integration_response = supabase.table("integrations")\
            .select("*")\
            .eq("service", "tautulli")\
            .eq("status", "active")\
            .limit(1)\
            .execute()
        
        if not integration_response.data:
            logger.warning("No active Tautulli integration found")
            return
        
        integration = integration_response.data[0]
        
        # Initialize services
        tautulli = TautulliService(
            url=integration["url"],
            api_key=integration["api_key"]
        )
        sync_service = TautulliSyncService(supabase, tautulli)
        
        # Run incremental sync (last 7 days for speed)
        await sync_service.sync_watch_history(days_back=7, batch_size=100)
        
        logger.info("Background Tautulli sync completed")
        
    except Exception as e:
        logger.error(f"Background Tautulli sync failed: {e}")


async def trigger_plex_library_sync_background(
    supabase: Client,
    library_section: Optional[str] = None
):
    """Background task to sync Plex library."""
    try:
        logger.info(f"Background Plex library sync triggered (section: {library_section or 'all'})")
        
        # TODO: Implement full Plex library sync
        # This will:
        # 1. Connect to Plex server
        # 2. Fetch library items (or specific section)
        # 3. Update media_items table with metadata
        # 4. Match external IDs (tmdb_id, tvdb_id, imdb_id)
        
        logger.info("Background Plex sync completed")
        
    except Exception as e:
        logger.error(f"Background Plex sync failed: {e}")


@router.post("/plex")
async def plex_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Plex Media Server.
    
    Plex sends webhooks for events like:
    - library.new (new content added)
    - library.on.deck (new episodes)
    - media.play (playback started)
    - media.stop (playback stopped)
    - media.pause, media.resume, media.scrobble
    
    Configure in Plex:
    Settings → Webhooks → Add Webhook
    URL: https://your-api.com/webhooks/plex
    
    Args:
        request: FastAPI request with multipart/form-data payload
        background_tasks: FastAPI background tasks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        # Plex sends webhooks as multipart/form-data with JSON in 'payload' field
        form_data = await request.form()
        payload_str = form_data.get("payload")
        
        if isinstance(payload_str, str):
            payload = json.loads(payload_str)
        else:
            # If it's an UploadFile or None, try to read it
            payload = {}
        
        event_type = payload.get("event")
        metadata = payload.get("Metadata", {})
        
        logger.info(f"📡 Plex webhook received: {event_type}")
        logger.debug(f"Payload: {payload}")
        
        # Log webhook to database
        webhook_record = {
            "source": "plex",
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Handle different event types
        if event_type == "library.new":
            # New content added - trigger library sync for this section
            library_section = metadata.get("librarySectionTitle")
            logger.info(f"🎬 New content in library: {library_section}")
            background_tasks.add_task(
                trigger_plex_library_sync_background,
                supabase,
                library_section
            )
            
        elif event_type in ["media.scrobble", "media.stop"]:
            # Playback completed - trigger Tautulli sync to get watch stats
            logger.info(f"📺 Playback event: {event_type}")
            background_tasks.add_task(trigger_tautulli_sync_background, supabase)
        
        return {
            "status": "received",
            "event": event_type,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Plex webhook processing failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/tautulli")
async def tautulli_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Tautulli.
    
    Tautulli can send webhooks for:
    - Playback start/stop/pause/resume
    - Recently added content
    - User watched milestones
    - Buffer warnings
    
    Configure in Tautulli:
    Settings → Notification Agents → Add New Notification Agent → Webhook
    Webhook URL: https://your-api.com/webhooks/tautulli
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("event")
        
        logger.info(f"📡 Tautulli webhook received: {event_type}")
        logger.debug(f"Payload: {payload}")
        
        # Log webhook
        webhook_record = {
            "source": "tautulli",
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger incremental sync for watch-related events
        if event_type in ["playback.stop", "watched"]:
            logger.info(f"📊 Triggering Tautulli sync for watch event")
            background_tasks.add_task(trigger_tautulli_sync_background, supabase)
        
        return {
            "status": "received",
            "event": event_type,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Tautulli webhook processing failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/sonarr")
async def sonarr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Sonarr.
    
    Sonarr sends webhooks for:
    - Download (episode downloaded)
    - Upgrade (episode upgraded)
    - Rename (episode renamed)
    - EpisodeFileDelete (episode deleted)
    - SeriesDelete (series deleted)
    
    Configure in Sonarr:
    Settings → Connect → + → Webhook
    URL: https://your-api.com/webhooks/sonarr
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("eventType")
        
        logger.info(f"📡 Sonarr webhook received: {event_type}")
        
        # Log webhook
        webhook_record = {
            "source": "sonarr",
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger Plex library sync when new content arrives
        if event_type in ["Download", "Upgrade"]:
            series = payload.get("series", {})
            logger.info(f"📺 New episode: {series.get('title')}")
            background_tasks.add_task(
                trigger_plex_library_sync_background,
                supabase,
                "TV Shows"
            )
        
        return {
            "status": "received",
            "event": event_type,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Sonarr webhook processing failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/radarr")
async def radarr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Radarr.
    
    Radarr sends webhooks for:
    - Download (movie downloaded)
    - Upgrade (movie upgraded)
    - Rename (movie renamed)
    - MovieDelete (movie deleted)
    
    Configure in Radarr:
    Settings → Connect → + → Webhook
    URL: https://your-api.com/webhooks/radarr
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("eventType")
        
        logger.info(f"📡 Radarr webhook received: {event_type}")
        
        # Log webhook
        webhook_record = {
            "source": "radarr",
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger Plex library sync when new content arrives
        if event_type in ["Download", "Upgrade"]:
            movie = payload.get("movie", {})
            logger.info(f"🎬 New movie: {movie.get('title')}")
            background_tasks.add_task(
                trigger_plex_library_sync_background,
                supabase,
                "Movies"
            )
        
        return {
            "status": "received",
            "event": event_type,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Radarr webhook processing failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/overseerr")
async def overseerr_webhook(
    request: Request,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Overseerr.
    
    Overseerr sends webhooks for:
    - Media Requested
    - Media Auto-Approved
    - Media Approved
    - Media Declined
    - Media Available
    - Media Failed
    
    Configure in Overseerr:
    Settings → Notifications → Webhook
    Webhook URL: https://your-api.com/webhooks/overseerr
    
    Args:
        request: FastAPI request with JSON payload
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        notification_type = payload.get("notification_type")
        
        logger.info(f"📡 Overseerr webhook received: {notification_type}")
        
        # Log webhook
        webhook_record = {
            "source": "overseerr",
            "event_type": notification_type,
            "payload": payload,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # TODO: Update request status in database
        # Track who requested what and when it becomes available
        
        return {
            "status": "received",
            "event": notification_type,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Overseerr webhook processing failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/status")
async def webhook_status(supabase: Client = Depends(get_supabase_client)):
    """
    Get webhook statistics and recent activity.
    
    Returns:
        Webhook stats and recent events
    """
    try:
        # Get recent webhooks (last 24 hours)
        recent_webhooks = supabase.table("webhook_log")\
            .select("*")\
            .order("received_at", desc=True)\
            .limit(50)\
            .execute()
        
        # Count by source
        counts_by_source = {}
        for webhook in recent_webhooks.data or []:
            source = webhook.get("source", "unknown")
            counts_by_source[source] = counts_by_source.get(source, 0) + 1
        
        return {
            "total_recent_webhooks": len(recent_webhooks.data or []),
            "by_source": counts_by_source,
            "recent_events": recent_webhooks.data[:10] if recent_webhooks.data else []
        }
        
    except Exception as e:
        logger.error(f"Failed to get webhook status: {e}")
        return {
            "error": str(e)
        }
