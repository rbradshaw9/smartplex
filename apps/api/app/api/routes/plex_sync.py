"""
Streaming Plex Library Sync with Real-Time Progress.

Uses Server-Sent Events (SSE) to stream sync progress to the client.
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from plexapi.myplex import MyPlexAccount
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user
from app.core.logging import get_logger
from app.core.plex_connection import PlexConnectionManager

router = APIRouter()
logger = get_logger("plex.sync")


async def sync_library_generator(
    user_id: str,
    plex_token: str,
    supabase: Client
) -> AsyncGenerator[str, None]:
    """
    Generator that yields SSE (Server-Sent Events) for real-time sync progress.
    
    Yields progress updates in format:
    data: {"current": 10, "total": 100, "title": "Movie Name", "eta_seconds": 45}
    """
    
    conn_manager = PlexConnectionManager(supabase)
    start_time = datetime.now(timezone.utc)
    
    try:
        # Step 1: Connect to Plex
        yield f'data: {{"status": "connecting", "message": "Connecting to Plex account..."}}\n\n'
        
        account = MyPlexAccount(token=plex_token)
        resources = account.resources()
        
        if not resources:
            yield f'data: {{"status": "error", "message": "No Plex servers found"}}\n\n'
            return
        
        # Step 2: Connect to servers
        servers_connected = 0
        total_items = 0
        synced_items = 0
        
        for resource in resources:
            if resource.product != 'Plex Media Server':
                continue
            
            try:
                yield f'data: {{"status": "connecting", "message": "Connecting to {resource.name}..."}}\n\n'
                
                server = await conn_manager.connect_to_server(resource, plex_token, user_id)
                if not server:
                    continue
                
                servers_connected += 1
                
                # Get or create server record
                server_record = supabase.table('servers').upsert({
                    'user_id': user_id,
                    'name': server.friendlyName,
                    'url': server._baseurl,
                    'machine_id': server.machineIdentifier,
                    'platform': server.platform,
                    'version': server.version,
                    'status': 'online',
                    'last_seen_at': datetime.now(timezone.utc).isoformat(),
                }, on_conflict='user_id,machine_id').execute()
                
                if not server_record.data:
                    continue
                
                server_id = server_record.data[0]['id']
                
                # Get library sections
                sections = server.library.sections()
                movie_sections = [s for s in sections if s.type in ['movie', 'show']]
                
                # Count total items first
                yield f'data: {{"status": "counting", "message": "Counting library items..."}}\n\n'
                
                for section in movie_sections:
                    try:
                        section_size = section.totalSize
                        total_items += section_size
                    except:
                        pass
                
                yield f'data: {{"status": "syncing", "total": {total_items}, "current": 0, "message": "Starting sync..."}}\n\n'
                
                # Now sync each section
                for section in movie_sections:
                    section_name = section.title
                    
                    try:
                        items = section.all()
                        
                        for item in items:
                            synced_items += 1
                            
                            # Extract metadata
                            item_type = 'movie' if section.type == 'movie' else 'show'
                            title = getattr(item, 'title', 'Unknown')
                            
                            # Extract IDs from guids
                            tmdb_id = None
                            tvdb_id = None
                            imdb_id = None
                            
                            for guid in getattr(item, 'guids', []):
                                guid_id = guid.id
                                if 'tmdb://' in guid_id:
                                    tmdb_id = guid_id.split('tmdb://')[1]
                                elif 'tvdb://' in guid_id:
                                    tvdb_id = guid_id.split('tvdb://')[1]
                                elif 'imdb://' in guid_id:
                                    imdb_id = guid_id.split('imdb://')[1]
                            
                            # Calculate file size
                            file_size_bytes = 0
                            try:
                                for media in getattr(item, 'media', []):
                                    for part in getattr(media, 'parts', []):
                                        file_size_bytes += getattr(part, 'size', 0)
                            except:
                                pass
                            
                            file_size_mb = round(file_size_bytes / (1024 * 1024), 2) if file_size_bytes > 0 else None
                            
                            # Upsert to database
                            media_data = {
                                'server_id': server_id,
                                'plex_id': str(item.ratingKey),
                                'title': title,
                                'type': item_type,
                                'year': getattr(item, 'year', None),
                                'rating': getattr(item, 'rating', None),
                                'duration_ms': getattr(item, 'duration', None),
                                'date_added': getattr(item, 'addedAt', datetime.now(timezone.utc)).isoformat(),
                                'summary': getattr(item, 'summary', None),
                                'poster_url': getattr(item, 'thumb', None),
                                'tmdb_id': tmdb_id,
                                'tvdb_id': tvdb_id,
                                'imdb_id': imdb_id,
                                'file_size_mb': file_size_mb,
                                'genres': [g.tag for g in getattr(item, 'genres', [])]
                            }
                            
                            try:
                                supabase.table('media_items').upsert(
                                    media_data,
                                    on_conflict='server_id,plex_id'
                                ).execute()
                            except Exception as db_error:
                                logger.error(f"Failed to upsert {title}: {db_error}")
                            
                            # Calculate ETA
                            elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
                            items_per_second = synced_items / elapsed_seconds if elapsed_seconds > 0 else 0
                            remaining_items = total_items - synced_items
                            eta_seconds = int(remaining_items / items_per_second) if items_per_second > 0 else 0
                            
                            # Send progress update every item (could throttle to every N items if needed)
                            progress_data = {
                                "status": "syncing",
                                "current": synced_items,
                                "total": total_items,
                                "title": title,
                                "section": section_name,
                                "eta_seconds": eta_seconds,
                                "items_per_second": round(items_per_second, 1)
                            }
                            
                            yield f'data: {progress_data}\n\n'
                            
                            # Small delay to prevent overwhelming the client
                            await asyncio.sleep(0.01)
                    
                    except Exception as section_error:
                        logger.error(f"Failed to sync section {section_name}: {section_error}")
                        yield f'data: {{"status": "warning", "message": "Failed to sync {section_name}"}}\n\n'
                
            except Exception as server_error:
                logger.error(f"Failed to connect to server {resource.name}: {server_error}")
                yield f'data: {{"status": "warning", "message": "Failed to connect to {resource.name}"}}\n\n'
                continue
        
        # Complete
        duration_seconds = int((datetime.now(timezone.utc) - start_time).total_seconds())
        
        completion_data = {
            "status": "complete",
            "current": synced_items,
            "total": total_items,
            "duration_seconds": duration_seconds,
            "servers_connected": servers_connected,
            "message": f"✅ Successfully synced {synced_items} items in {duration_seconds}s"
        }
        
        yield f'data: {completion_data}\n\n'
        
        # Log sync event
        try:
            supabase.table('sync_events').insert({
                'sync_type': 'plex',
                'user_id': user_id,
                'trigger_type': 'manual',
                'status': 'completed',
                'items_discovered': synced_items,
                'items_new': 0,  # Would need to track this separately
                'items_updated': synced_items,
                'duration_ms': duration_seconds * 1000,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as log_error:
            logger.error(f"Failed to log sync event: {log_error}")
    
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        yield f'data: {{"status": "error", "message": "Sync failed: {str(e)}"}}\n\n'


@router.get("/sync-library-stream")
async def sync_library_stream(
    plex_token: str = Query(..., description="Plex authentication token"),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Stream library sync progress using Server-Sent Events (SSE).
    
    Client should listen for 'data' events with JSON progress updates.
    
    Progress format:
    - status: "connecting" | "counting" | "syncing" | "complete" | "error"
    - current: number of items synced so far
    - total: total items to sync
    - title: current item being synced
    - section: current library section
    - eta_seconds: estimated seconds remaining
    - items_per_second: sync speed
    """
    
    return StreamingResponse(
        sync_library_generator(user['id'], plex_token, supabase),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/storage-info")
async def get_storage_info(
    plex_token: str = Query(..., description="Plex authentication token"),
    user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get storage information from Plex servers.
    
    Returns total capacity, used space, and available space.
    """
    
    try:
        conn_manager = PlexConnectionManager(supabase)
        account = MyPlexAccount(token=plex_token)
        
        storage_info = {
            "servers": [],
            "total_capacity_bytes": 0,
            "total_used_bytes": 0,
            "total_available_bytes": 0
        }
        
        for resource in account.resources():
            if resource.product != 'Plex Media Server':
                continue
            
            try:
                server = await conn_manager.connect_to_server(resource, plex_token, user['id'])
                if not server:
                    continue
                
                # Try to get storage info from server
                # Note: Plex doesn't always expose this easily, may need to query filesystem
                sections = server.library.sections()
                
                total_size_bytes = 0
                item_count = 0
                
                for section in sections:
                    if section.type in ['movie', 'show']:
                        try:
                            # Get all items in section
                            items = section.all()
                            item_count += len(items)
                            
                            # Sum up file sizes
                            for item in items:
                                for media in getattr(item, 'media', []):
                                    for part in getattr(media, 'parts', []):
                                        total_size_bytes += getattr(part, 'size', 0)
                        except Exception as section_error:
                            logger.error(f"Failed to get storage for {section.title}: {section_error}")
                            continue
                
                server_info = {
                    "name": server.friendlyName,
                    "machine_id": server.machineIdentifier,
                    "used_bytes": total_size_bytes,
                    "used_gb": round(total_size_bytes / (1024**3), 2),
                    "item_count": item_count
                }
                
                storage_info["servers"].append(server_info)
                storage_info["total_used_bytes"] += total_size_bytes
            
            except Exception as server_error:
                logger.error(f"Failed to get storage for {resource.name}: {server_error}")
                continue
        
        # Convert totals to human-readable
        storage_info["total_used_gb"] = round(storage_info["total_used_bytes"] / (1024**3), 2)
        storage_info["total_used_tb"] = round(storage_info["total_used_bytes"] / (1024**4), 2)
        
        return storage_info
    
    except Exception as e:
        logger.error(f"Failed to get storage info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get storage info: {str(e)}"
        )
