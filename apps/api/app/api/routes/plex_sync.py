"""
Streaming Plex Library Sync with Real-Time Progress.

Uses Server-Sent Events (SSE) to stream sync progress to the client.
"""

import asyncio
import json
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

# Global sync cancellation tracking (in production, use Redis or DB)
_active_syncs: dict[str, bool] = {}  # user_id -> is_cancelled


async def get_current_storage_stats(supabase: Client) -> dict:
    """Calculate current storage statistics from database."""
    try:
        storage_query = supabase.table('media_items')\
            .select('file_size_mb')\
            .not_.is_('file_size_mb', 'null')\
            .execute()
        
        total_size_mb = sum(item.get('file_size_mb', 0) or 0 for item in (storage_query.data or []))
        total_used_gb = round(total_size_mb / 1024, 2)
        
        # Get capacity config
        capacity_config = supabase.table('system_config')\
            .select('value')\
            .eq('key', 'storage_capacity')\
            .execute()
        
        total_capacity_gb = None
        if capacity_config.data and len(capacity_config.data) > 0:
            capacity_data = capacity_config.data[0]['value']
            total_capacity_gb = capacity_data.get('total_gb')
        
        return {
            "total_used_gb": total_used_gb,
            "total_capacity_gb": total_capacity_gb,
            "free_gb": round(total_capacity_gb - total_used_gb, 2) if total_capacity_gb else None,
            "used_percentage": round((total_used_gb / total_capacity_gb) * 100, 1) if total_capacity_gb else None
        }
    except Exception as e:
        logger.warning(f"Failed to calculate storage stats: {e}")
        return {}


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
    last_storage_update = 0  # Track when we last sent storage update
    synced_plex_ids = set()  # Track all Plex IDs we see during sync for orphan cleanup
    
    # Initialize sync state
    _active_syncs[user_id] = False  # False = not cancelled
    
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
                
                if not server_record.data:  # type: ignore
                    continue
                
                server_id = server_record.data[0]['id']  # type: ignore
                
                # Get library sections
                sections = server.library.sections()
                movie_sections = [s for s in sections if s.type in ['movie', 'show']]
                
                # Count total items first (episodes for shows, movies for movies)
                yield f'data: {{"status": "counting", "message": "Counting library items..."}}\n\n'
                
                for section in movie_sections:
                    try:
                        if section.type == 'show':
                            # Count episodes, not shows
                            for show in section.all():
                                try:
                                    total_items += len(show.episodes())
                                except:
                                    pass
                        else:
                            # Count movies directly
                            total_items += section.totalSize
                    except Exception as e:
                        logger.warning(f"Failed to count section {section.title}: {e}")
                        pass
                
                yield f'data: {{"status": "syncing", "total": {total_items}, "current": 0, "message": "Starting sync..."}}\n\n'
                
                # Now sync each section
                for section in movie_sections:
                    section_name = section.title
                    
                    try:
                        items = section.all()
                        
                        for item in items:
                            # Check for cancellation
                            if _active_syncs.get(user_id, False):
                                logger.info(f"Sync cancelled by user {user_id}")
                                yield f'data: {{"status": "cancelled", "message": "Sync cancelled by user", "current": {synced_items}, "total": {total_items}}}\n\n'
                                _active_syncs.pop(user_id, None)
                                return
                            
                            # For TV shows, iterate through all episodes
                            if section.type == 'show':
                                try:
                                    # Get all episodes for this show
                                    episodes = item.episodes()
                                    
                                    for episode in episodes:
                                        # Check for cancellation
                                        if _active_syncs.get(user_id, False):
                                            logger.info(f"Sync cancelled by user {user_id}")
                                            yield f'data: {{"status": "cancelled", "message": "Sync cancelled by user", "current": {synced_items}, "total": {total_items}}}\n\n'
                                            _active_syncs.pop(user_id, None)
                                            return
                                        
                                        synced_items += 1
                                        
                                        # Extract metadata
                                        title = getattr(episode, 'title', 'Unknown')
                                        show_title = getattr(item, 'title', 'Unknown')
                                        season_title = getattr(episode, 'seasonTitle', f'Season {episode.seasonNumber}') if hasattr(episode, 'seasonNumber') else None
                                        
                                        # Extract IDs from show guids (episodes inherit show IDs)
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
                                            for media in getattr(episode, 'media', []):
                                                for part in getattr(media, 'parts', []):
                                                    file_size_bytes += getattr(part, 'size', 0)
                                        except:
                                            pass
                                        
                                        file_size_mb = round(file_size_bytes / (1024 * 1024), 2) if file_size_bytes > 0 else None
                                        
                                        # Upsert episode to database
                                        media_data = {
                                            'server_id': server_id,
                                            'plex_id': str(episode.ratingKey),
                                            'title': title,
                                            'type': 'episode',
                                            'grandparent_title': show_title,
                                            'year': getattr(episode, 'year', None),
                                            'duration_ms': getattr(episode, 'duration', None),
                                            'tmdb_id': tmdb_id,
                                            'tvdb_id': tvdb_id,
                                            'imdb_id': imdb_id
                                        }
                                        
                                        try:
                                            supabase.table('media_items').upsert(
                                                media_data,
                                                on_conflict='server_id,plex_id'
                                            ).execute()
                                            synced_plex_ids.add((server_id, str(episode.ratingKey)))
                                        except Exception as db_error:
                                            logger.error(f"Failed to upsert episode {title}: {db_error}")
                                        
                                        # Calculate ETA
                                        elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
                                        items_per_second = synced_items / elapsed_seconds if elapsed_seconds > 0 else 0
                                        remaining_items = total_items - synced_items
                                        eta_seconds = int(remaining_items / items_per_second) if items_per_second > 0 else 0
                                        
                                        # Send progress update
                                        progress_data = {
                                            "status": "syncing",
                                            "current": synced_items,
                                            "total": total_items,
                                            "title": f"{show_title} - S{episode.seasonNumber:02d}E{episode.episodeNumber:02d}",
                                            "section": section_name,
                                            "eta_seconds": eta_seconds,
                                            "items_per_second": round(items_per_second, 1)
                                        }
                                        
                                        # Add storage update every 100 items
                                        if synced_items - last_storage_update >= 100:
                                            storage_stats = await get_current_storage_stats(supabase)
                                            progress_data["storage"] = storage_stats
                                            last_storage_update = synced_items
                                        
                                        yield f'data: {json.dumps(progress_data)}\n\n'
                                        
                                        # Small delay to prevent overwhelming the client
                                        await asyncio.sleep(0.01)
                                        
                                except Exception as show_error:
                                    logger.error(f"Failed to sync episodes for show {item.title}: {show_error}")
                                    continue
                            else:
                                # Handle movies
                                synced_items += 1
                                
                                # Extract metadata
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
                                    'type': 'movie',
                                    'year': getattr(item, 'year', None),
                                    'duration_ms': getattr(item, 'duration', None),
                                    'tmdb_id': tmdb_id,
                                    'tvdb_id': tvdb_id,
                                    'imdb_id': imdb_id
                                }
                                
                                try:
                                    supabase.table('media_items').upsert(
                                        media_data,
                                        on_conflict='server_id,plex_id'
                                    ).execute()
                                    synced_plex_ids.add((server_id, str(item.ratingKey)))
                                except Exception as db_error:
                                    logger.error(f"Failed to upsert {title}: {db_error}")
                                
                                # Calculate ETA
                                elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
                                items_per_second = synced_items / elapsed_seconds if elapsed_seconds > 0 else 0
                                remaining_items = total_items - synced_items
                                eta_seconds = int(remaining_items / items_per_second) if items_per_second > 0 else 0
                                
                                # Send progress update
                                progress_data = {
                                    "status": "syncing",
                                    "current": synced_items,
                                    "total": total_items,
                                    "title": title,
                                    "section": section_name,
                                    "eta_seconds": eta_seconds,
                                    "items_per_second": round(items_per_second, 1)
                                }
                                
                                # Add storage update every 100 items
                                if synced_items - last_storage_update >= 100:
                                    storage_stats = await get_current_storage_stats(supabase)
                                    progress_data["storage"] = storage_stats
                                    last_storage_update = synced_items
                                
                                yield f'data: {json.dumps(progress_data)}\n\n'
                                
                                # Small delay to prevent overwhelming the client
                                await asyncio.sleep(0.01)
                    
                    except Exception as section_error:
                        logger.error(f"Failed to sync section {section_name}: {section_error}")
                        yield f'data: {{"status": "warning", "message": "Failed to sync {section_name}"}}\n\n'
                
            except Exception as server_error:
                logger.error(f"Failed to connect to server {resource.name}: {server_error}")
                yield f'data: {{"status": "warning", "message": "Failed to connect to {resource.name}"}}\n\n'
                continue
        
        # Cleanup orphaned media (items in DB that no longer exist in Plex)
        yield f'data: {{"status": "syncing", "message": "Cleaning up orphaned media..."}}\n\n'
        
        orphaned_count = 0
        try:
            # Get all media items from database
            all_db_items = supabase.table('media_items').select('id, server_id, plex_id, title').execute()
            
            if all_db_items.data:
                for db_item in all_db_items.data:
                    server_id_key = (db_item['server_id'], db_item['plex_id'])
                    
                    # If this item wasn't seen during sync, it's orphaned
                    if server_id_key not in synced_plex_ids:
                        try:
                            supabase.table('media_items').delete().eq('id', db_item['id']).execute()
                            orphaned_count += 1
                            logger.info(f"Removed orphaned media: {db_item['title']} (plex_id: {db_item['plex_id']})")
                        except Exception as delete_error:
                            logger.error(f"Failed to delete orphaned item {db_item['title']}: {delete_error}")
            
            if orphaned_count > 0:
                logger.info(f"Cleaned up {orphaned_count} orphaned media items")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup orphaned media: {cleanup_error}")
        
        # Complete
        duration_seconds = int((datetime.now(timezone.utc) - start_time).total_seconds())
        
        # Get final storage stats (after cleanup)
        final_storage = await get_current_storage_stats(supabase)
        
        completion_message = f"✅ Successfully synced {synced_items} items in {duration_seconds}s"
        if orphaned_count > 0:
            completion_message += f" (removed {orphaned_count} orphaned items)"
        
        completion_data = {
            "status": "complete",
            "current": synced_items,
            "total": total_items,
            "duration_seconds": duration_seconds,
            "servers_connected": servers_connected,
            "orphaned_removed": orphaned_count,
            "message": completion_message,
            "storage": final_storage
        }
        
        yield f'data: {json.dumps(completion_data)}\n\n'
        
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
    finally:
        # Cleanup sync state
        _active_syncs.pop(user_id, None)


@router.post("/cancel-sync")
async def cancel_sync(
    user: dict = Depends(get_current_user),
):
    """
    Cancel an in-progress library sync for the current user.
    """
    user_id = user['id']
    
    if user_id in _active_syncs:
        _active_syncs[user_id] = True  # Mark as cancelled
        logger.info(f"Sync cancellation requested for user {user_id}")
        return {"message": "Sync cancellation requested"}
    else:
        return {"message": "No active sync found"}


@router.get("/sync-library-stream")
async def sync_library_stream(
    plex_token: str = Query(..., description="Plex authentication token"),
    auth_token: str = Query(..., description="Supabase auth token for SSE"),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Stream library sync progress using Server-Sent Events (SSE).
    
    Note: EventSource doesn't support custom headers, so we pass auth token as query param.
    This is only for SSE endpoints where headers aren't supported.
    
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
    
    # Validate auth token since EventSource can't send Authorization header
    try:
        user_response = supabase.auth.get_user(auth_token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid auth token")
        
        # Get user details
        user_result = supabase.table('users').select('*').eq('id', user_response.user.id).single().execute()
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_result.data
        
    except Exception as e:
        logger.error(f"Auth validation failed: {e}")
        raise HTTPException(status_code=403, detail="Authentication failed")
    
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
    Get storage information from database (faster than querying Plex).
    
    Returns used space calculated from media_items table.
    Includes total capacity from system configuration if set.
    """
    
    try:
        # Get storage from database (much faster than querying Plex)
        storage_query = supabase.table('media_items')\
            .select('file_size_mb, type')\
            .not_.is_('file_size_mb', 'null')\
            .execute()
        
        total_size_mb = 0
        total_items = 0
        by_type = {}
        
        if storage_query.data:
            for item in storage_query.data:
                size_mb = item.get('file_size_mb', 0) or 0
                item_type = item.get('type', 'unknown')
                
                total_size_mb += size_mb
                total_items += 1
                
                if item_type not in by_type:
                    by_type[item_type] = {'count': 0, 'size_mb': 0}
                by_type[item_type]['count'] += 1
                by_type[item_type]['size_mb'] += size_mb
        
        # Convert to human-readable
        total_used_gb = round(total_size_mb / 1024, 2)
        total_used_tb = round(total_size_mb / (1024 * 1024), 2)
        
        # Format by_type for response
        by_type_formatted = {}
        for media_type, stats in by_type.items():
            by_type_formatted[media_type] = {
                'count': stats['count'],
                'size_gb': round(stats['size_mb'] / 1024, 2),
                'size_tb': round(stats['size_mb'] / (1024 * 1024), 2)
            }
        
        # Get total capacity from system config
        total_capacity_gb = None
        free_gb = None
        used_percentage = None
        capacity_configured = False
        
        try:
            capacity_config = supabase.table('system_config')\
                .select('value')\
                .eq('key', 'storage_capacity')\
                .execute()
            
            if capacity_config.data and len(capacity_config.data) > 0:
                capacity_data = capacity_config.data[0]['value']
                total_capacity_gb = capacity_data.get('total_gb')
                
                if total_capacity_gb:
                    capacity_configured = True
                    free_gb = round(total_capacity_gb - total_used_gb, 2)
                    used_percentage = round((total_used_gb / total_capacity_gb) * 100, 1)
        except Exception as config_error:
            logger.warning(f"Could not fetch storage capacity config: {config_error}")
        
        storage_info = {
            "total_items": total_items,
            "total_used_gb": total_used_gb,
            "total_used_tb": total_used_tb,
            "total_capacity_gb": total_capacity_gb,
            "free_gb": free_gb,
            "used_percentage": used_percentage,
            "capacity_configured": capacity_configured,
            "by_type": by_type_formatted,
        }
        
        return storage_info
    
    except Exception as e:
        logger.error(f"Failed to get storage info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get storage info: {str(e)}"
        )
