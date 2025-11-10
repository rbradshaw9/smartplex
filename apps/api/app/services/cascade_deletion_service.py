"""
Comprehensive Deletion Service with Cascade Support.

Handles deletion across ALL systems to prevent auto-redownload:
1. Plex - Delete from library
2. Sonarr/Radarr - Remove from *arr (prevents auto-redownload)
3. Overseerr - Delete request (allows re-request if needed)

Logs everything to deletion_events table for audit trail.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx

from supabase import Client
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount

from app.core.logging import get_logger
from app.core.plex_connection import PlexConnectionManager

logger = get_logger("cascade_deletion_service")


class CascadeDeletionService:
    """
    Service for deleting media across all integrated systems.
    
    Ensures complete removal to prevent:
    - Orphaned Plex items
    - Sonarr/Radarr auto-redownload
    - User confusion about request status
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.conn_manager = PlexConnectionManager(supabase)
    
    async def delete_media_item(
        self,
        media_item: Dict[str, Any],
        user_id: str,
        deletion_rule_id: Optional[str] = None,
        deletion_reason: str = "manual",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a media item from all integrated systems.
        
        Args:
            media_item: Media item dict from database (must have id, plex_id, title, type, server_id)
            user_id: User performing the deletion
            deletion_rule_id: Optional deletion rule that triggered this
            deletion_reason: Why it's being deleted
            dry_run: If True, log what would happen without actually deleting
            
        Returns:
            Dict with deletion results and status
        """
        start_time = datetime.now(timezone.utc)
        
        # Create deletion event record
        deletion_event = {
            "media_item_id": media_item['id'],
            "plex_id": media_item['plex_id'],
            "title": media_item['title'],
            "media_type": media_item.get('type'),
            "deletion_rule_id": deletion_rule_id,
            "deletion_reason": deletion_reason,
            "deleted_by_user_id": user_id,
            "dry_run": dry_run,
            "status": "pending",
            "file_size_mb": media_item.get('file_size_mb')
        }
        
        # Insert event to track progress
        event_result = self.supabase.table("deletion_events").insert(deletion_event).execute()
        event_id = event_result.data[0]['id'] if event_result.data else None
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting deletion of '{media_item['title']}' (event_id: {event_id})")
        
        results = {
            "event_id": event_id,
            "title": media_item['title'],
            "plex": {"success": False, "error": None},
            "sonarr": {"success": False, "error": None, "skipped": True},
            "radarr": {"success": False, "error": None, "skipped": True},
            "overseerr": {"success": False, "error": None, "skipped": True},
            "overall_status": "failed",
            "dry_run": dry_run
        }
        
        # 1. Delete from Plex
        try:
            plex_result = await self._delete_from_plex(
                media_item=media_item,
                user_id=user_id,
                dry_run=dry_run
            )
            results["plex"] = plex_result
            
            if plex_result["success"] and event_id:
                self.supabase.table("deletion_events").update({
                    "deleted_from_plex": True,
                    "deleted_from_plex_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", event_id).execute()
                
        except Exception as e:
            logger.error(f"Plex deletion failed: {e}", exc_info=True)
            results["plex"]["error"] = str(e)
        
        # 2. Delete from Sonarr (if TV show)
        if media_item.get('type') in ['show', 'season', 'episode']:
            try:
                results["sonarr"]["skipped"] = False
                sonarr_result = await self._delete_from_sonarr(
                    media_item=media_item,
                    user_id=user_id,
                    dry_run=dry_run
                )
                results["sonarr"] = sonarr_result
                
                if sonarr_result["success"] and event_id:
                    self.supabase.table("deletion_events").update({
                        "deleted_from_sonarr": True,
                        "deleted_from_sonarr_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", event_id).execute()
                    
            except Exception as e:
                logger.error(f"Sonarr deletion failed: {e}", exc_info=True)
                results["sonarr"]["error"] = str(e)
        
        # 3. Delete from Radarr (if movie)
        if media_item.get('type') == 'movie':
            try:
                results["radarr"]["skipped"] = False
                radarr_result = await self._delete_from_radarr(
                    media_item=media_item,
                    user_id=user_id,
                    dry_run=dry_run
                )
                results["radarr"] = radarr_result
                
                if radarr_result["success"] and event_id:
                    self.supabase.table("deletion_events").update({
                        "deleted_from_radarr": True,
                        "deleted_from_radarr_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", event_id).execute()
                    
            except Exception as e:
                logger.error(f"Radarr deletion failed: {e}", exc_info=True)
                results["radarr"]["error"] = str(e)
        
        # 4. Delete from Overseerr (remove any requests)
        try:
            results["overseerr"]["skipped"] = False
            overseerr_result = await self._delete_from_overseerr(
                media_item=media_item,
                user_id=user_id,
                dry_run=dry_run
            )
            results["overseerr"] = overseerr_result
            
            if overseerr_result["success"] and event_id:
                self.supabase.table("deletion_events").update({
                    "deleted_from_overseerr": True,
                    "deleted_from_overseerr_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", event_id).execute()
                
        except Exception as e:
            logger.error(f"Overseerr deletion failed: {e}", exc_info=True)
            results["overseerr"]["error"] = str(e)
        
        # Determine overall status
        plex_success = results["plex"]["success"]
        arr_success = (
            (results["sonarr"]["skipped"] or results["sonarr"]["success"]) and
            (results["radarr"]["skipped"] or results["radarr"]["success"])
        )
        overseerr_success = results["overseerr"]["skipped"] or results["overseerr"]["success"]
        
        if plex_success and arr_success and overseerr_success:
            results["overall_status"] = "completed"
        elif plex_success:
            results["overall_status"] = "partial"
        else:
            results["overall_status"] = "failed"
        
        # Update final event status
        if event_id:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            self.supabase.table("deletion_events").update({
                "status": results["overall_status"],
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", event_id).execute()
            
            # Log to admin activity log
            self.supabase.table("admin_activity_log").insert({
                "user_id": user_id,
                "action_type": "deletion",
                "action": "media_deleted",
                "resource_type": "media_item",
                "resource_id": media_item['id'],
                "resource_name": media_item['title'],
                "details": results,
                "status": results["overall_status"],
                "items_affected": 1,
                "duration_ms": duration_ms
            }).execute()
        
        logger.info(f"Deletion {'simulation' if dry_run else 'completed'}: {results['overall_status']}")
        
        return results
    
    async def _delete_from_plex(
        self,
        media_item: Dict[str, Any],
        user_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Delete item from Plex library."""
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting from Plex: {media_item['title']}")
            
            # Get server details
            server_result = self.supabase.table("servers").select("*").eq("id", media_item['server_id']).single().execute()
            if not server_result.data:
                return {"success": False, "error": "Server not found"}
            
            server_data = server_result.data
            
            # Get user's Plex token
            user_result = self.supabase.table("users").select("plex_token").eq("id", user_id).single().execute()
            if not user_result.data or not user_result.data.get('plex_token'):
                return {"success": False, "error": "No Plex token found"}
            
            plex_token = user_result.data['plex_token']
            
            if dry_run:
                return {
                    "success": True,
                    "message": f"Would delete '{media_item['title']}' (plex_id: {media_item['plex_id']}) from Plex",
                    "dry_run": True
                }
            
            # Connect to Plex
            if server_data.get('preferred_connection_url'):
                server = PlexServer(
                    baseurl=server_data['preferred_connection_url'],
                    token=plex_token,
                    timeout=10
                )
            else:
                # Fallback to MyPlex
                account = MyPlexAccount(token=plex_token)
                for resource in account.resources():
                    if resource.clientIdentifier == server_data['machine_id']:
                        server = await self.conn_manager.connect_to_server(resource, plex_token, user_id)
                        break
                else:
                    return {"success": False, "error": "Could not connect to Plex server"}
            
            # Find and delete the item
            try:
                # Fetch the item by rating key (plex_id)
                item = server.fetchItem(int(media_item['plex_id']))
                
                # Delete it
                item.delete()
                
                logger.info(f"✅ Successfully deleted '{media_item['title']}' from Plex")
                return {
                    "success": True,
                    "message": f"Deleted from Plex library"
                }
                
            except Exception as item_error:
                logger.error(f"Failed to delete Plex item: {item_error}")
                return {"success": False, "error": f"Plex API error: {str(item_error)}"}
            
        except Exception as e:
            logger.error(f"Plex deletion error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _delete_from_sonarr(
        self,
        media_item: Dict[str, Any],
        user_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Delete series from Sonarr (prevents auto-redownload)."""
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Removing from Sonarr: {media_item['title']}")
            
            # Get Sonarr integration
            integration_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("service", "sonarr")\
                .eq("enabled", True)\
                .maybe_single()\
                .execute()
            
            if not integration_result.data:
                logger.info("No active Sonarr integration found")
                return {"success": True, "message": "No Sonarr integration", "skipped": True}
            
            integration = integration_result.data
            tvdb_id = media_item.get('tvdb_id')
            
            if not tvdb_id:
                logger.info("No TVDB ID found for series")
                return {"success": True, "message": "No TVDB ID", "skipped": True}
            
            if dry_run:
                return {
                    "success": True,
                    "message": f"Would remove series (TVDB: {tvdb_id}) from Sonarr",
                    "dry_run": True
                }
            
            # Call Sonarr API to find and delete series
            async with httpx.AsyncClient() as client:
                # Find series by TVDB ID
                response = await client.get(
                    f"{integration['url']}/api/v3/series",
                    headers={"X-Api-Key": integration['api_key']},
                    params={"tvdbId": tvdb_id},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {"success": False, "error": f"Sonarr API error: {response.status_code}"}
                
                series_list = response.json()
                
                if not series_list or len(series_list) == 0:
                    logger.info(f"Series not found in Sonarr (TVDB: {tvdb_id})")
                    return {"success": True, "message": "Not in Sonarr", "skipped": True}
                
                series = series_list[0]
                series_id = series['id']
                
                # Delete series and files
                delete_response = await client.delete(
                    f"{integration['url']}/api/v3/series/{series_id}",
                    headers={"X-Api-Key": integration['api_key']},
                    params={"deleteFiles": "true"},
                    timeout=30.0
                )
                
                if delete_response.status_code in [200, 204]:
                    logger.info(f"✅ Successfully removed from Sonarr: {media_item['title']}")
                    return {"success": True, "message": "Removed from Sonarr"}
                else:
                    return {"success": False, "error": f"Sonarr delete failed: {delete_response.status_code}"}
            
        except Exception as e:
            logger.error(f"Sonarr deletion error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _delete_from_radarr(
        self,
        media_item: Dict[str, Any],
        user_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Delete movie from Radarr (prevents auto-redownload)."""
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Removing from Radarr: {media_item['title']}")
            
            # Get Radarr integration
            integration_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("service", "radarr")\
                .eq("enabled", True)\
                .maybe_single()\
                .execute()
            
            if not integration_result.data:
                logger.info("No active Radarr integration found")
                return {"success": True, "message": "No Radarr integration", "skipped": True}
            
            integration = integration_result.data
            tmdb_id = media_item.get('tmdb_id')
            
            if not tmdb_id:
                logger.info("No TMDB ID found for movie")
                return {"success": True, "message": "No TMDB ID", "skipped": True}
            
            if dry_run:
                return {
                    "success": True,
                    "message": f"Would remove movie (TMDB: {tmdb_id}) from Radarr",
                    "dry_run": True
                }
            
            # Call Radarr API to find and delete movie
            async with httpx.AsyncClient() as client:
                # Find movie by TMDB ID
                response = await client.get(
                    f"{integration['url']}/api/v3/movie",
                    headers={"X-Api-Key": integration['api_key']},
                    params={"tmdbId": tmdb_id},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {"success": False, "error": f"Radarr API error: {response.status_code}"}
                
                movies = response.json()
                
                if not movies or len(movies) == 0:
                    logger.info(f"Movie not found in Radarr (TMDB: {tmdb_id})")
                    return {"success": True, "message": "Not in Radarr", "skipped": True}
                
                movie = movies[0]
                movie_id = movie['id']
                
                # Delete movie and files
                delete_response = await client.delete(
                    f"{integration['url']}/api/v3/movie/{movie_id}",
                    headers={"X-Api-Key": integration['api_key']},
                    params={"deleteFiles": "true", "addImportExclusion": "false"},
                    timeout=30.0
                )
                
                if delete_response.status_code in [200, 204]:
                    logger.info(f"✅ Successfully removed from Radarr: {media_item['title']}")
                    return {"success": True, "message": "Removed from Radarr"}
                else:
                    return {"success": False, "error": f"Radarr delete failed: {delete_response.status_code}"}
            
        except Exception as e:
            logger.error(f"Radarr deletion error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _delete_from_overseerr(
        self,
        media_item: Dict[str, Any],
        user_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Delete request from Overseerr (allows re-request)."""
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Removing from Overseerr: {media_item['title']}")
            
            # Get Overseerr integration
            integration_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("service", "overseerr")\
                .eq("enabled", True)\
                .maybe_single()\
                .execute()
            
            if not integration_result.data:
                logger.info("No active Overseerr integration found")
                return {"success": True, "message": "No Overseerr integration", "skipped": True}
            
            integration = integration_result.data
            tmdb_id = media_item.get('tmdb_id')
            media_type = "tv" if media_item.get('type') in ['show', 'season', 'episode'] else "movie"
            
            if not tmdb_id:
                logger.info("No TMDB ID found")
                return {"success": True, "message": "No TMDB ID", "skipped": True}
            
            if dry_run:
                return {
                    "success": True,
                    "message": f"Would remove requests for {media_type} (TMDB: {tmdb_id}) from Overseerr",
                    "dry_run": True
                }
            
            # Call Overseerr API to find and delete requests
            async with httpx.AsyncClient() as client:
                # Find media by TMDB ID
                response = await client.get(
                    f"{integration['url']}/api/v1/media",
                    headers={"X-Api-Key": integration['api_key']},
                    params={"tmdbId": tmdb_id, "type": media_type},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.info(f"Media not found in Overseerr: {response.status_code}")
                    return {"success": True, "message": "Not in Overseerr", "skipped": True}
                
                media_data = response.json()
                
                if not media_data or 'requests' not in media_data:
                    return {"success": True, "message": "No requests found", "skipped": True}
                
                # Delete all requests for this media
                deleted_count = 0
                for request in media_data.get('requests', []):
                    request_id = request['id']
                    delete_response = await client.delete(
                        f"{integration['url']}/api/v1/request/{request_id}",
                        headers={"X-Api-Key": integration['api_key']},
                        timeout=10.0
                    )
                    
                    if delete_response.status_code in [200, 204]:
                        deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"✅ Removed {deleted_count} request(s) from Overseerr: {media_item['title']}")
                    return {"success": True, "message": f"Removed {deleted_count} requests"}
                else:
                    return {"success": True, "message": "No requests to remove", "skipped": True}
            
        except Exception as e:
            logger.error(f"Overseerr deletion error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
