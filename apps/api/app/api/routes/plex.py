"""
Plex API endpoints for fetching servers, libraries, and media.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import httpx

from app.core.supabase import get_supabase_client, get_current_user
from app.core.cache import PlexCache
from supabase import Client

router = APIRouter(prefix="/plex", tags=["plex"])


class PlexServerResponse(BaseModel):
    """Plex server information."""
    name: str
    machine_identifier: str
    product: str
    platform: str
    platform_version: str
    owned: bool
    home: bool


class PlexLibraryResponse(BaseModel):
    """Plex library information."""
    title: str
    type: str
    key: str
    agent: str
    scanner: str
    language: str
    uuid: str
    updated_at: int
    created_at: int
    scanned_at: int
    content: bool
    directory: bool
    content_changed_at: int
    hidden: int


@router.get("/servers")
async def get_plex_servers(
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> List[PlexServerResponse]:
    """
    Get list of Plex servers accessible to the authenticated user.
    
    Uses the stored Plex token to fetch available servers from Plex.tv.
    """
    try:
        # Get user's Plex token from database
        user_data = supabase.table('users').select('*').eq('id', user['id']).single().execute()
        
        if not user_data.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Plex token from user profile - it's stored during auth
        # We need to fetch it from the session or localStorage on client side
        # For now, let's use the plex_user_id to make API calls
        
        # TODO: Store plex_token securely in database
        raise HTTPException(
            status_code=501,
            detail="Plex token retrieval not yet implemented. Token should be sent from client."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Plex servers: {str(e)}"
        )


@router.get("/servers/{server_id}/libraries")
async def get_server_libraries(
    server_id: str,
    plex_token: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get libraries from a specific Plex server.
    
    Args:
        server_id: Plex server machine identifier
        plex_token: Plex authentication token
    """
    try:
        # Connect to Plex account
        account = MyPlexAccount(token=plex_token)
        
        # Find the specified server
        server = None
        for resource in account.resources():
            if resource.clientIdentifier == server_id:
                server = resource.connect()
                break
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Get all libraries
        libraries = []
        for section in server.library.sections():
            libraries.append({
                "title": section.title,
                "type": section.type,
                "key": section.key,
                "agent": section.agent,
                "scanner": section.scanner,
                "language": section.language,
                "uuid": section.uuid,
                "updated_at": section.updatedAt,
                "created_at": section.createdAt,
                "scanned_at": section.scannedAt,
            })
        
        return libraries
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch libraries: {str(e)}"
        )


@router.get("/watch-history")
async def get_watch_history(
    plex_token: str,
    limit: int = 50,
    force_refresh: bool = False,
    user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get comprehensive user viewing data from Plex including:
    - Watch history (recently watched items)
    - Ratings (likes/dislikes) 
    - Watchlist items
    - On deck (in-progress items)
    
    Uses caching to speed up repeated requests. Cache TTL: 15 minutes.
    
    Args:
        plex_token: Plex authentication token
        limit: Maximum number of items per category
        force_refresh: Skip cache and force fresh data from Plex
    """
    try:
        # Initialize cache
        cache = PlexCache(supabase, user['id'])
        
        # Try to get cached data first (unless force refresh)
        if not force_refresh:
            cached_data = await cache.get_cached_watch_history()
            if cached_data:
                # Add sync info
                sync_info = await cache.get_last_sync_info()
                if sync_info:
                    cached_data['sync_info'] = sync_info
                cached_data['from_cache'] = True
                return cached_data
        
        # Connect to Plex account
        account = MyPlexAccount(token=plex_token)
        
        # Initialize result structure
        result = {
            "watch_history": [],
            "on_deck": [],
            "watchlist": [],
            "ratings": {
                "liked": [],
                "disliked": []
            },
            "stats": {
                "total_watched": 0,
                "total_hours": 0,
                "servers_connected": 0
            }
        }
        
        # Get watchlist from Plex account (across all servers)
        try:
            watchlist = account.watchlist()
            for item in watchlist[:limit]:
                result["watchlist"].append({
                    "title": item.title,
                    "type": item.type,
                    "year": getattr(item, 'year', None),
                    "rating": getattr(item, 'rating', None),
                    "thumb": getattr(item, 'thumb', None),
                    "added_at": item.addedAt.isoformat() if hasattr(item, 'addedAt') and item.addedAt else None,
                })
        except Exception as watchlist_error:
            print(f"Failed to fetch watchlist: {watchlist_error}")
        
        # Process each server
        for resource in account.resources():
            try:
                # Try to connect with shorter timeout to reduce wait time
                server = resource.connect(timeout=10)
                result["stats"]["servers_connected"] += 1
                
                # Get On Deck (in-progress items)
                try:
                    for item in server.library.onDeck():
                        result["on_deck"].append({
                            "title": item.title,
                            "type": item.type,
                            "year": getattr(item, 'year', None),
                            "rating": getattr(item, 'rating', None),
                            "duration": getattr(item, 'duration', None),
                            "view_offset": getattr(item, 'viewOffset', 0),
                            "progress": (getattr(item, 'viewOffset', 0) / getattr(item, 'duration', 1) * 100) if getattr(item, 'duration', 0) > 0 else 0,
                            "thumb": getattr(item, 'thumb', None),
                            "server_name": server.friendlyName,
                        })
                except Exception as deck_error:
                    print(f"Failed to fetch on deck for {server.friendlyName}: {deck_error}")
                
                # Get watch history from all library sections
                for section in server.library.sections():
                    try:
                        # Get all items and filter by view count
                        for item in section.all():
                            # Skip items that haven't been watched
                            view_count = getattr(item, 'viewCount', 0)
                            if view_count == 0:
                                continue
                                
                            # Track stats
                            duration = getattr(item, 'duration', 0)
                            result["stats"]["total_watched"] += view_count
                            result["stats"]["total_hours"] += (duration / 1000 / 60 / 60) * view_count  # Convert ms to hours
                            
                            # Get user rating if exists
                            user_rating = getattr(item, 'userRating', None)
                            
                            watch_data = {
                                "title": item.title,
                                "type": item.type,
                                "year": getattr(item, 'year', None),
                                "rating": getattr(item, 'rating', None),
                                "content_rating": getattr(item, 'contentRating', None),
                                "duration": duration,
                                "last_viewed_at": item.lastViewedAt.isoformat() if hasattr(item, 'lastViewedAt') and item.lastViewedAt else None,
                                "view_count": view_count,
                                "user_rating": user_rating,
                                "thumb": getattr(item, 'thumb', None),
                                "server_name": server.friendlyName,
                                "library": section.title,
                                "summary": getattr(item, 'summary', None),
                                "genres": [g.tag for g in getattr(item, 'genres', [])],
                            }
                            
                            result["watch_history"].append(watch_data)
                            
                            # Categorize by rating
                            if user_rating is not None:
                                if user_rating >= 7:  # Plex uses 1-10 scale
                                    result["ratings"]["liked"].append(watch_data)
                                elif user_rating <= 4:
                                    result["ratings"]["disliked"].append(watch_data)
                                    
                    except Exception as section_error:
                        print(f"Failed to fetch history from {section.title}: {section_error}")
                        continue
                        
            except Exception as server_error:
                # Skip servers that can't be reached
                print(f"Failed to connect to server {resource.name}: {server_error}")
                continue
        
        # Sort watch history by last viewed date
        result["watch_history"].sort(key=lambda x: x.get('last_viewed_at', ''), reverse=True)
        result["watch_history"] = result["watch_history"][:limit]
        
        # Round stats
        result["stats"]["total_hours"] = round(result["stats"]["total_hours"], 1)
        result["from_cache"] = False
        
        # Cache the fresh data for next time
        # Get or create server record (use first connected server for now)
        if result["stats"]["servers_connected"] > 0:
            try:
                # Get first server's machine ID for caching
                first_server = None
                for resource in account.resources():
                    try:
                        server = resource.connect(timeout=5)
                        first_server = server
                        break
                    except:
                        continue
                
                if first_server:
                    # Get or create server record in database
                    server_result = supabase.table('servers').upsert({
                        'user_id': user['id'],
                        'name': first_server.friendlyName,
                        'url': first_server._baseurl,
                        'machine_id': first_server.machineIdentifier,
                        'platform': first_server.platform,
                        'version': first_server.version,
                        'status': 'online',
                        'last_seen_at': datetime.utcnow().isoformat(),
                    }, on_conflict='user_id,machine_id').execute()
                    
                    if server_result.data:
                        server_id = server_result.data[0]['id']
                        # Cache the watch history
                        await cache.cache_watch_history(result, server_id)
                        
            except Exception as cache_error:
                # Don't fail the request if caching fails
                print(f"Warning: Failed to cache watch history: {cache_error}")
        
        # Add sync info
        sync_info = await cache.get_last_sync_info()
        if sync_info:
            result['sync_info'] = sync_info
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch watch data: {str(e)}"
        )
