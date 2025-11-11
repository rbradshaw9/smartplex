"""
Plex Collection Manager for Deletion Candidates.

Creates and maintains a "Leaving Soon ⏰" collection in Plex
to show users which content will be deleted soon.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from supabase import Client

from app.core.logging import get_logger
from app.core.plex_connection import PlexConnectionManager

logger = get_logger("plex_collections")


class PlexCollectionManager:
    """Manages Plex collections for deletion candidates."""
    
    LEAVING_SOON_COLLECTION = "Leaving Soon ⏰"
    LEAVING_SOON_SUMMARY = "These items are candidates for deletion based on inactivity. Watch them soon if you want to keep them!"
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.conn_manager = PlexConnectionManager(supabase)
    
    async def update_leaving_soon_collection(
        self,
        server_id: str,
        user_id: str,
        candidates: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Update or create the "Leaving Soon" collection in Plex.
        
        Args:
            server_id: Server UUID
            user_id: Admin user performing the action
            candidates: List of deletion candidates (from scan_for_candidates)
            dry_run: If True, only log what would be done
            
        Returns:
            Dict with success status and details
        """
        try:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updating Leaving Soon collection with {len(candidates)} items")
            
            # Get server details
            server_result = self.supabase.table("servers").select("*").eq("id", server_id).single().execute()
            if not server_result.data:
                return {"success": False, "error": "Server not found"}
            
            server_data = server_result.data
            
            # TODO: Plex token is not stored in database - it's in frontend localStorage
            # This feature requires token to be passed as parameter or stored in integrations
            # For now, skip Plex collection updates since token is not available
            logger.warning("Plex token not available - collection update feature temporarily disabled")
            return {
                "success": False, 
                "error": "Plex token not available in database. Collection feature requires frontend token to be passed as parameter.",
                "skipped": True
            }
            
            if dry_run:
                return {
                    "success": True,
                    "message": f"Would update 'Leaving Soon' collection with {len(candidates)} items",
                    "dry_run": True,
                    "candidates_count": len(candidates)
                }
            
            # Connect to Plex server
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
            
            # Get movie and TV libraries
            movie_section = None
            tv_section = None
            
            for section in server.library.sections():
                if section.type == 'movie':
                    movie_section = section
                elif section.type == 'show':
                    tv_section = section
            
            if not movie_section and not tv_section:
                return {"success": False, "error": "No movie or TV libraries found"}
            
            # Separate candidates by type
            movies_to_add = []
            shows_to_add = []
            
            for candidate in candidates:
                try:
                    plex_id = int(candidate['plex_id'])
                    media_type = candidate['type']
                    
                    if media_type == 'movie' and movie_section:
                        try:
                            item = server.fetchItem(plex_id)
                            movies_to_add.append(item)
                        except Exception as e:
                            logger.warning(f"Could not fetch movie {candidate['title']}: {e}")
                    
                    elif media_type in ['show', 'season', 'episode'] and tv_section:
                        try:
                            item = server.fetchItem(plex_id)
                            # For seasons/episodes, get the parent show
                            if media_type in ['season', 'episode']:
                                item = item.show()
                            shows_to_add.append(item)
                        except Exception as e:
                            logger.warning(f"Could not fetch show {candidate['title']}: {e}")
                
                except Exception as e:
                    logger.error(f"Error processing candidate {candidate.get('title', 'unknown')}: {e}")
                    continue
            
            # Remove duplicates (in case multiple episodes from same show)
            shows_to_add = list({show.ratingKey: show for show in shows_to_add}.values())
            
            logger.info(f"Adding to collection: {len(movies_to_add)} movies, {len(shows_to_add)} shows")
            
            # Create or update collection for movies
            movies_added = 0
            if movies_to_add and movie_section:
                try:
                    collection = self._get_or_create_collection(
                        movie_section,
                        self.LEAVING_SOON_COLLECTION,
                        self.LEAVING_SOON_SUMMARY
                    )
                    
                    # Clear existing items
                    for item in collection.items():
                        collection.removeItems(item)
                    
                    # Add new items
                    collection.addItems(movies_to_add)
                    movies_added = len(movies_to_add)
                    
                    logger.info(f"✅ Updated movie collection with {movies_added} items")
                except Exception as e:
                    logger.error(f"Failed to update movie collection: {e}")
            
            # Create or update collection for TV shows
            shows_added = 0
            if shows_to_add and tv_section:
                try:
                    collection = self._get_or_create_collection(
                        tv_section,
                        self.LEAVING_SOON_COLLECTION,
                        self.LEAVING_SOON_SUMMARY
                    )
                    
                    # Clear existing items
                    for item in collection.items():
                        collection.removeItems(item)
                    
                    # Add new items
                    collection.addItems(shows_to_add)
                    shows_added = len(shows_to_add)
                    
                    logger.info(f"✅ Updated TV collection with {shows_added} items")
                except Exception as e:
                    logger.error(f"Failed to update TV collection: {e}")
            
            return {
                "success": True,
                "message": f"Updated 'Leaving Soon' collection",
                "movies_added": movies_added,
                "shows_added": shows_added,
                "total_items": movies_added + shows_added
            }
        
        except Exception as e:
            logger.error(f"Failed to update Leaving Soon collection: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _get_or_create_collection(self, section, title: str, summary: str):
        """Get existing collection or create new one."""
        try:
            # Try to find existing collection
            collection = section.collection(title)
            logger.info(f"Found existing collection: {title}")
            return collection
        except:
            # Collection doesn't exist, create it
            logger.info(f"Creating new collection: {title}")
            # Create with first dummy item, will be replaced
            items = section.all()
            if not items:
                raise Exception(f"No items in {section.title} library to create collection")
            
            collection = section.createCollection(
                title=title,
                items=items[:1]  # Need at least 1 item to create collection
            )
            
            # Update summary
            collection.edit(summary=summary)
            
            # Clear the dummy item
            for item in collection.items():
                collection.removeItems(item)
            
            return collection
    
    async def clear_leaving_soon_collection(
        self,
        server_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Clear all items from the Leaving Soon collection.
        
        Useful after deletions are executed or rules are disabled.
        """
        try:
            logger.info("Clearing Leaving Soon collection")
            
            # Get server and connect
            server_result = self.supabase.table("servers").select("*").eq("id", server_id).single().execute()
            if not server_result.data:
                return {"success": False, "error": "Server not found"}
            
            server_data = server_result.data
            
            # TODO: Plex token not stored in database - see update_leaving_soon_collection
            logger.warning("Plex token not available - collection clear feature temporarily disabled")
            return {
                "success": False,
                "error": "Plex token not available in database",
                "skipped": True
            }
            
            # Connect to server
            if server_data.get('preferred_connection_url'):
                server = PlexServer(baseurl=server_data['preferred_connection_url'], token=plex_token, timeout=10)
            else:
                account = MyPlexAccount(token=plex_token)
                for resource in account.resources():
                    if resource.clientIdentifier == server_data['machine_id']:
                        server = await self.conn_manager.connect_to_server(resource, plex_token, user_id)
                        break
                else:
                    return {"success": False, "error": "Could not connect"}
            
            cleared_sections = []
            
            # Clear from all sections
            for section in server.library.sections():
                if section.type in ['movie', 'show']:
                    try:
                        collection = section.collection(self.LEAVING_SOON_COLLECTION)
                        for item in collection.items():
                            collection.removeItems(item)
                        cleared_sections.append(section.title)
                        logger.info(f"Cleared collection from {section.title}")
                    except:
                        # Collection doesn't exist in this section
                        pass
            
            return {
                "success": True,
                "message": f"Cleared Leaving Soon collection from {len(cleared_sections)} sections",
                "sections": cleared_sections
            }
        
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
