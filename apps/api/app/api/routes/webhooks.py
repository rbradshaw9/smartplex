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


async def trigger_tautulli_sync_background(supabase: Client, user_id: str):
    """Background task to sync Tautulli data for a specific user."""
    try:
        logger.info(f"Background Tautulli sync triggered by webhook for user {user_id}")
        
        # Get active Tautulli integration for this user
        integration_response = supabase.table("integrations")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("service", "tautulli")\
            .eq("status", "active")\
            .limit(1)\
            .execute()
        
        if not integration_response.data:
            logger.warning(f"No active Tautulli integration found for user {user_id}")
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
    user_id: str,
    server_id: str,
    library_section: Optional[str] = None
):
    """Background task to sync Plex library for a specific user/server."""
    try:
        logger.info(f"Background Plex library sync triggered for user {user_id}, server {server_id} (section: {library_section or 'all'})")
        
        # TODO: Implement full Plex library sync
        # This will:
        # 1. Get server connection details from database
        # 2. Connect to Plex server using preferred_connection_url or try all URLs
        # 3. Fetch library items (or specific section)
        # 4. Update media_items table with metadata
        # 5. Match external IDs (tmdb_id, tvdb_id, imdb_id)
        # 6. Associate items with this server_id and user_id
        
        logger.info(f"Background Plex sync completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Background Plex sync failed for user {user_id}: {e}")


@router.post("/plex")
@router.post("/plex/{user_id}")
async def plex_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Plex Media Server.
    
    Supports both global and user-specific webhook URLs:
    - Global: /api/webhooks/plex (matches by server machine_id)
    - User-specific: /api/webhooks/plex/{user_id} (for multi-tenancy)
    
    Plex sends webhooks for events like:
    - library.new (new content added)
    - library.on.deck (new episodes)
    - media.play (playback started)
    - media.stop (playback stopped)
    - media.pause, media.resume, media.scrobble
    
    Configure in Plex:
    Settings → Webhooks → Add Webhook
    URL: https://your-api.com/api/webhooks/plex/{your_user_id}
    
    Args:
        request: FastAPI request with multipart/form-data payload
        background_tasks: FastAPI background tasks
        user_id: Optional user ID for user-specific webhooks
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
        server_info = payload.get("Server", {})
        machine_id = server_info.get("uuid")
        
        logger.info(f"📡 Plex webhook received: {event_type} (machine_id: {machine_id}, user_id: {user_id})")
        logger.debug(f"Payload: {payload}")
        
        # Identify which user owns this Plex server
        resolved_user_id = None
        server_id = None
        
        if user_id:
            # User-specific webhook URL - validate user exists
            user_response = supabase.table("users").select("id").eq("id", user_id).execute()
            if user_response.data:
                resolved_user_id = user_id
                # Get server_id for this user and machine_id
                if machine_id:
                    server_response = supabase.table("servers")\
                        .select("id")\
                        .eq("user_id", user_id)\
                        .eq("machine_id", machine_id)\
                        .execute()
                    if server_response.data:
                        server_id = server_response.data[0]["id"]
        elif machine_id:
            # Global webhook URL - look up user by machine_id
            server_response = supabase.table("servers")\
                .select("id, user_id")\
                .eq("machine_id", machine_id)\
                .execute()
            
            if server_response.data:
                resolved_user_id = server_response.data[0]["user_id"]
                server_id = server_response.data[0]["id"]
                logger.info(f"Matched server machine_id {machine_id} to user {resolved_user_id}")
            else:
                logger.warning(f"No server found with machine_id: {machine_id}")
        
        # Log webhook to database
        webhook_record = {
            "source": "plex",
            "event_type": event_type,
            "payload": payload,
            "user_id": resolved_user_id,
            "server_id": server_id,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Handle different event types (only if we identified the user and server)
        if resolved_user_id and server_id:
            if event_type == "library.new":
                # New content added - trigger library sync for this section
                library_section = metadata.get("librarySectionTitle")
                logger.info(f"🎬 New content in library: {library_section} for user {resolved_user_id}")
                background_tasks.add_task(
                    trigger_plex_library_sync_background,
                    supabase,
                    resolved_user_id,
                    server_id,
                    library_section
                )
                
            elif event_type in ["media.scrobble", "media.stop"]:
                # Playback completed - trigger Tautulli sync to get watch stats
                logger.info(f"📺 Playback event: {event_type} for user {resolved_user_id}")
                background_tasks.add_task(
                    trigger_tautulli_sync_background,
                    supabase,
                    resolved_user_id
                )
        else:
            logger.warning(f"Could not identify user for webhook - no background task triggered")
        
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
@router.post("/tautulli/{user_id}")
async def tautulli_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Tautulli.
    
    Supports both global and user-specific webhook URLs:
    - Global: /api/webhooks/tautulli (uses first active Tautulli integration)
    - User-specific: /api/webhooks/tautulli/{user_id} (recommended for multi-user)
    
    Tautulli can send webhooks for:
    - Playback start/stop/pause/resume
    - Recently added content
    - User watched milestones
    - Buffer warnings
    
    Configure in Tautulli:
    Settings → Notification Agents → Add New Notification Agent → Webhook
    Webhook URL: https://your-api.com/api/webhooks/tautulli/{your_user_id}
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        user_id: Optional user ID for user-specific webhooks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("event")
        
        logger.info(f"📡 Tautulli webhook received: {event_type} (user_id: {user_id})")
        logger.debug(f"Payload: {payload}")
        
        # Identify user - if user_id not provided, try to find active Tautulli integration
        resolved_user_id = user_id
        if not resolved_user_id:
            # Find first active Tautulli integration (legacy behavior)
            integration_response = supabase.table("integrations")\
                .select("user_id")\
                .eq("service", "tautulli")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            if integration_response.data:
                resolved_user_id = integration_response.data[0]["user_id"]
        
        # Log webhook
        webhook_record = {
            "source": "tautulli",
            "event_type": event_type,
            "payload": payload,
            "user_id": resolved_user_id,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger incremental sync for watch-related events
        if resolved_user_id and event_type in ["playback.stop", "watched"]:
            logger.info(f"📊 Triggering Tautulli sync for user {resolved_user_id}")
            background_tasks.add_task(trigger_tautulli_sync_background, supabase, resolved_user_id)
        elif not resolved_user_id:
            logger.warning("Could not identify user for Tautulli webhook")
        
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
@router.post("/sonarr/{user_id}")
async def sonarr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Sonarr.
    
    Supports both global and user-specific webhook URLs:
    - Global: /api/webhooks/sonarr (uses first active Sonarr integration)
    - User-specific: /api/webhooks/sonarr/{user_id} (recommended for multi-user)
    
    Sonarr sends webhooks for:
    - Download (episode downloaded)
    - Upgrade (episode upgraded)
    - Rename (episode renamed)
    - EpisodeFileDelete (episode deleted)
    - SeriesDelete (series deleted)
    
    Configure in Sonarr:
    Settings → Connect → + → Webhook
    URL: https://your-api.com/api/webhooks/sonarr/{your_user_id}
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        user_id: Optional user ID for user-specific webhooks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("eventType")
        
        logger.info(f"📡 Sonarr webhook received: {event_type} (user_id: {user_id})")
        
        # Identify user
        resolved_user_id = user_id
        server_id = None
        if not resolved_user_id:
            # Find first active Sonarr integration (legacy behavior)
            integration_response = supabase.table("integrations")\
                .select("user_id, server_id")\
                .eq("service", "sonarr")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            if integration_response.data:
                resolved_user_id = integration_response.data[0]["user_id"]
                server_id = integration_response.data[0].get("server_id")
        else:
            # Get server_id for this user's Sonarr integration
            integration_response = supabase.table("integrations")\
                .select("server_id")\
                .eq("user_id", user_id)\
                .eq("service", "sonarr")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            if integration_response.data:
                server_id = integration_response.data[0].get("server_id")
        
        # Log webhook
        webhook_record = {
            "source": "sonarr",
            "event_type": event_type,
            "payload": payload,
            "user_id": resolved_user_id,
            "server_id": server_id,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger Plex library sync when new content arrives
        if resolved_user_id and server_id and event_type in ["Download", "Upgrade"]:
            series = payload.get("series", {})
            logger.info(f"📺 New episode: {series.get('title')} for user {resolved_user_id}")
            background_tasks.add_task(
                trigger_plex_library_sync_background,
                supabase,
                resolved_user_id,
                server_id,
                "TV Shows"
            )
        elif not resolved_user_id:
            logger.warning("Could not identify user for Sonarr webhook")
        
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
@router.post("/radarr/{user_id}")
async def radarr_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Receive webhooks from Radarr.
    
    Supports both global and user-specific webhook URLs:
    - Global: /api/webhooks/radarr (uses first active Radarr integration)
    - User-specific: /api/webhooks/radarr/{user_id} (recommended for multi-user)
    
    Radarr sends webhooks for:
    - Download (movie downloaded)
    - Upgrade (movie upgraded)
    - Rename (movie renamed)
    - MovieDelete (movie deleted)
    
    Configure in Radarr:
    Settings → Connect → + → Webhook
    URL: https://your-api.com/api/webhooks/radarr/{your_user_id}
    
    Args:
        request: FastAPI request with JSON payload
        background_tasks: FastAPI background tasks
        user_id: Optional user ID for user-specific webhooks
        supabase: Supabase client
        
    Returns:
        Webhook acknowledgment
    """
    try:
        payload = await request.json()
        event_type = payload.get("eventType")
        
        logger.info(f"📡 Radarr webhook received: {event_type} (user_id: {user_id})")
        
        # Identify user
        resolved_user_id = user_id
        server_id = None
        if not resolved_user_id:
            # Find first active Radarr integration (legacy behavior)
            integration_response = supabase.table("integrations")\
                .select("user_id, server_id")\
                .eq("service", "radarr")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            if integration_response.data:
                resolved_user_id = integration_response.data[0]["user_id"]
                server_id = integration_response.data[0].get("server_id")
        else:
            # Get server_id for this user's Radarr integration
            integration_response = supabase.table("integrations")\
                .select("server_id")\
                .eq("user_id", user_id)\
                .eq("service", "radarr")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            if integration_response.data:
                server_id = integration_response.data[0].get("server_id")
        
        # Log webhook
        webhook_record = {
            "source": "radarr",
            "event_type": event_type,
            "payload": payload,
            "user_id": resolved_user_id,
            "server_id": server_id,
            "received_at": datetime.utcnow().isoformat(),
            "processed": False
        }
        supabase.table("webhook_log").insert(webhook_record).execute()
        
        # Trigger Plex library sync when new content arrives
        if resolved_user_id and server_id and event_type in ["Download", "Upgrade"]:
            movie = payload.get("movie", {})
            logger.info(f"🎬 New movie: {movie.get('title')} for user {resolved_user_id}")
            background_tasks.add_task(
                trigger_plex_library_sync_background,
                supabase,
                resolved_user_id,
                server_id,
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
