"""
Hybrid Analytics Service with Tautulli-First, Plex API Fallback.

Provides watch data and analytics from best available source:
1. Tautulli API (best - per-user detail)
2. Plex API (fallback - aggregate viewCount/lastViewedAt)

This ensures the app works even without Tautulli configured.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

import httpx
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from supabase import Client

from app.core.logging import get_logger
from app.core.plex_connection import PlexConnectionManager

logger = get_logger("analytics_service")

DataSource = Literal["tautulli", "plex_api", "none"]


class AnalyticsService:
    """
    Hybrid analytics service with automatic fallback.
    
    Transparently uses best available data source:
    - Tautulli: Full per-user watch history
    - Plex API: Aggregate viewCount across all users
    - None: No watch data available
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.conn_manager = PlexConnectionManager(supabase)
    
    async def get_data_source(self, server_id: str) -> DataSource:
        """
        Determine which data source is available.
        
        Returns:
            "tautulli" if Tautulli integration active
            "plex_api" if only Plex available
            "none" if neither available
        """
        # Check for active Tautulli integration
        tautulli = await self._get_tautulli_integration(server_id)
        if tautulli:
            return "tautulli"
        
        # Check if we can connect to Plex
        server = await self._get_server(server_id)
        if server:
            return "plex_api"
        
        return "none"
    
    async def sync_watch_data(
        self,
        server_id: str,
        force_source: Optional[DataSource] = None
    ) -> Dict[str, Any]:
        """
        Sync watch data from best available source.
        
        Args:
            server_id: Server UUID
            force_source: Override automatic source detection
            
        Returns:
            Dict with sync results and data source used
        """
        try:
            # Determine data source
            if force_source:
                data_source = force_source
            else:
                data_source = await self.get_data_source(server_id)
            
            logger.info(f"Syncing watch data using source: {data_source}")
            
            if data_source == "tautulli":
                return await self._sync_from_tautulli(server_id)
            elif data_source == "plex_api":
                return await self._sync_from_plex_api(server_id)
            else:
                return {
                    "success": False,
                    "error": "No data source available",
                    "data_source": "none",
                    "items_synced": 0
                }
        
        except Exception as e:
            logger.error(f"Watch data sync failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data_source": "error",
                "items_synced": 0
            }
    
    async def _sync_from_tautulli(self, server_id: str) -> Dict[str, Any]:
        """Sync from Tautulli (existing functionality)."""
        integration = await self._get_tautulli_integration(server_id)
        if not integration:
            return {
                "success": False,
                "error": "Tautulli integration not found",
                "data_source": "tautulli",
                "items_synced": 0
            }
        
        # Use existing Tautulli sync logic
        # This is already implemented in tautulli_sync.py
        return {
            "success": True,
            "message": "Using existing Tautulli sync",
            "data_source": "tautulli",
            "note": "Tautulli sync should be called via existing endpoint"
        }
    
    async def _sync_from_plex_api(self, server_id: str) -> Dict[str, Any]:
        """
        Sync aggregate watch data from Plex API.
        
        Updates media_items with:
        - total_play_count (from viewCount)
        - last_watched_at (from lastViewedAt)
        """
        try:
            # Get server and connect
            server_data = await self._get_server(server_id)
            if not server_data:
                return {
                    "success": False,
                    "error": "Server not found",
                    "data_source": "plex_api",
                    "items_synced": 0
                }
            
            # Get admin's Plex token from integrations or use passed token
            # For now, we'll need the token passed from the frontend
            # TODO: Store admin token in integrations for server-side operations
            
            return {
                "success": False,
                "error": "Plex token required for aggregate sync (pass via parameter)",
                "data_source": "plex_api",
                "items_synced": 0,
                "note": "This will be implemented when token storage solution is added"
            }
        
        except Exception as e:
            logger.error(f"Plex API sync failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data_source": "plex_api",
                "items_synced": 0
            }
    
    async def sync_plex_aggregate_with_token(
        self,
        server_id: str,
        plex_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Sync Plex aggregate data with provided token.
        
        This is the working version that requires token from frontend.
        """
        items_updated = 0
        items_processed = 0
        
        try:
            logger.info(f"Starting Plex aggregate sync for server {server_id}")
            
            # Get server details
            server_result = self.supabase.table("servers")\
                .select("*")\
                .eq("id", server_id)\
                .single()\
                .execute()
            
            if not server_result.data:
                return {
                    "success": False,
                    "error": "Server not found",
                    "data_source": "plex_api",
                    "items_synced": 0
                }
            
            server_data = server_result.data
            
            # Connect to Plex
            plex_server = None
            if server_data.get('preferred_connection_url'):
                try:
                    plex_server = PlexServer(
                        baseurl=server_data['preferred_connection_url'],
                        token=plex_token,
                        timeout=10
                    )
                except Exception as e:
                    logger.warning(f"Direct connection failed: {e}, trying MyPlex")
            
            if not plex_server:
                account = MyPlexAccount(token=plex_token)
                for resource in account.resources():
                    if resource.clientIdentifier == server_data['machine_id']:
                        plex_server = await self.conn_manager.connect_to_server(
                            resource, plex_token, user_id
                        )
                        break
            
            if not plex_server:
                return {
                    "success": False,
                    "error": "Could not connect to Plex server",
                    "data_source": "plex_api",
                    "items_synced": 0
                }
            
            # Iterate through all library sections
            for section in plex_server.library.sections():
                if section.type not in ['movie', 'show']:
                    continue
                
                logger.info(f"Processing section: {section.title}")
                
                # Get all items in section
                for item in section.all():
                    items_processed += 1
                    
                    try:
                        # Get aggregate data from Plex
                        view_count = getattr(item, 'viewCount', 0) or 0
                        last_viewed_at = getattr(item, 'lastViewedAt', None)
                        
                        # Convert timestamp if exists
                        last_watched_dt = None
                        if last_viewed_at:
                            last_watched_dt = datetime.fromtimestamp(
                                last_viewed_at, tz=timezone.utc
                            ).isoformat()
                        
                        # Update media_item in database
                        update_result = self.supabase.table("media_items")\
                            .update({
                                "total_play_count": view_count,
                                "last_watched_at": last_watched_dt,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            })\
                            .eq("plex_id", str(item.ratingKey))\
                            .eq("server_id", server_id)\
                            .execute()
                        
                        if update_result.data:
                            items_updated += 1
                        
                        # Log progress every 100 items
                        if items_processed % 100 == 0:
                            logger.info(
                                f"Progress: {items_processed} processed, "
                                f"{items_updated} updated"
                            )
                    
                    except Exception as item_error:
                        logger.warning(
                            f"Failed to update {item.title}: {item_error}"
                        )
                        continue
            
            logger.info(
                f"✅ Plex aggregate sync complete: "
                f"{items_updated}/{items_processed} items updated"
            )
            
            return {
                "success": True,
                "message": f"Synced {items_updated} items from Plex API",
                "data_source": "plex_api",
                "items_synced": items_updated,
                "items_processed": items_processed
            }
        
        except Exception as e:
            logger.error(f"Plex aggregate sync failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data_source": "plex_api",
                "items_synced": items_updated
            }
    
    async def _get_tautulli_integration(
        self, 
        server_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get active Tautulli integration for server."""
        try:
            # Get server admin
            server_result = self.supabase.table("servers")\
                .select("user_id")\
                .eq("id", server_id)\
                .single()\
                .execute()
            
            if not server_result.data:
                return None
            
            admin_id = server_result.data['user_id']
            
            # Get Tautulli integration
            integration_result = self.supabase.table("integrations")\
                .select("*")\
                .eq("user_id", admin_id)\
                .eq("server_id", server_id)\
                .eq("service", "tautulli")\
                .eq("status", "active")\
                .limit(1)\
                .execute()
            
            if not integration_result.data or len(integration_result.data) == 0:
                return None
            
            return integration_result.data[0]
        
        except Exception as e:
            logger.error(f"Failed to get Tautulli integration: {e}")
            return None
    
    async def _get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server details."""
        try:
            result = self.supabase.table("servers")\
                .select("*")\
                .eq("id", server_id)\
                .single()\
                .execute()
            
            return result.data
        
        except Exception as e:
            logger.error(f"Failed to get server: {e}")
            return None
