"""
Plex connection utilities with caching for fast reconnections.
Reduces connection time from 30+ seconds to ~2 seconds by caching the working URL.
"""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import time
import asyncio
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexResource
from supabase import Client


class PlexConnectionManager:
    """
    Manages Plex server connections with intelligent URL caching.
    
    Problem: PlexAPI tries multiple URLs (local, remote, relay) with long timeouts.
    Solution: Cache the URL that worked and try it first next time.
    """
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.connection_timeout = 5  # Reduced from default 10s
        self.cache_duration_hours = 24  # How long to trust cached URL
    
    async def connect_to_server(
        self,
        resource: MyPlexResource,
        plex_token: str,
        user_id: str
    ) -> Optional[PlexServer]:
        """
        Connect to Plex server with caching optimization.
        
        Strategy:
        1. Check if we have a cached working URL (less than 24h old)
        2. If yes, try it first with short timeout (2s)
        3. If cached URL fails or doesn't exist, try all URLs
        4. Cache the URL that worked for next time
        
        Args:
            resource: MyPlexResource from account.resources()
            plex_token: Plex authentication token
            user_id: Current user ID for cache lookup
            
        Returns:
            Connected PlexServer or None if all connections failed
        """
        machine_id = resource.clientIdentifier
        
        # Try cached connection first
        cached_server = await self._try_cached_connection(
            machine_id, plex_token, user_id
        )
        if cached_server:
            return cached_server
        
        # No cache or cache failed - try all connection methods
        print(f"No cached connection for {resource.name}, trying all URLs...")
        return await self._connect_and_cache(
            resource, plex_token, user_id, machine_id
        )
    
    async def _try_cached_connection(
        self,
        machine_id: str,
        plex_token: str,
        user_id: str
    ) -> Optional[PlexServer]:
        """Try to connect using cached URL if available and recent."""
        try:
            # Look up cached connection info
            result = self.supabase.table('servers')\
                .select('preferred_connection_url, connection_tested_at, name')\
                .eq('machine_id', machine_id)\
                .eq('user_id', user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data or not result.data.get('preferred_connection_url'):
                return None
            
            server_data = result.data
            cached_url = server_data['preferred_connection_url']
            tested_at = server_data.get('connection_tested_at')
            
            # Check if cache is still fresh (within 24 hours)
            if tested_at:
                tested_time = datetime.fromisoformat(tested_at.replace('Z', '+00:00'))
                age_hours = (datetime.now(tested_time.tzinfo) - tested_time).total_seconds() / 3600
                
                if age_hours > self.cache_duration_hours:
                    print(f"Cached URL for {server_data['name']} is {age_hours:.1f}h old, refreshing...")
                    return None
            
            # Try cached URL with short timeout
            print(f"Trying cached URL for {server_data['name']}: {cached_url}")
            start_time = time.time()
            
            try:
                server = PlexServer(
                    baseurl=cached_url,
                    token=plex_token,
                    timeout=2  # Very short timeout for cached connection
                )
                
                # Test connection with a simple API call
                _ = server.machineIdentifier
                
                latency_ms = int((time.time() - start_time) * 1000)
                print(f"✅ Cached connection successful in {latency_ms}ms")
                
                # Update last tested time and latency
                self.supabase.table('servers')\
                    .update({
                        'connection_tested_at': datetime.utcnow().isoformat(),
                        'connection_latency_ms': latency_ms,
                        'status': 'online',
                        'last_seen_at': datetime.utcnow().isoformat()
                    })\
                    .eq('machine_id', machine_id)\
                    .eq('user_id', user_id)\
                    .execute()
                
                return server
                
            except Exception as e:
                print(f"⚠️ Cached connection failed: {e}")
                # Clear bad cache
                self.supabase.table('servers')\
                    .update({'preferred_connection_url': None})\
                    .eq('machine_id', machine_id)\
                    .eq('user_id', user_id)\
                    .execute()
                return None
                
        except Exception as e:
            print(f"Error checking cache: {e}")
            return None
    
    async def _connect_and_cache(
        self,
        resource: MyPlexResource,
        plex_token: str,
        user_id: str,
        machine_id: str
    ) -> Optional[PlexServer]:
        """
        Try all connection methods and cache the one that works.
        
        PlexAPI tries URLs in this order:
        1. Local LAN addresses (192.168.x.x, 10.x.x.x)
        2. Remote direct address (public IP/domain)
        3. Plex relay (slow, last resort)
        """
        try:
            start_time = time.time()
            
            # Let PlexAPI try its connection logic with our timeout
            server = resource.connect(timeout=self.connection_timeout)
            
            # Get the URL that worked
            working_url = server._baseurl
            latency_ms = int((time.time() - start_time) * 1000)
            
            print(f"✅ Connected to {resource.name} via {working_url} in {latency_ms}ms")
            
            # Upsert server record with cached connection
            self.supabase.table('servers').upsert({
                'user_id': user_id,
                'machine_id': machine_id,
                'name': resource.name,
                'url': working_url,
                'preferred_connection_url': working_url,  # Cache it!
                'connection_tested_at': datetime.utcnow().isoformat(),
                'connection_latency_ms': latency_ms,
                'platform': server.platform,
                'version': server.version,
                'status': 'online',
                'last_seen_at': datetime.utcnow().isoformat()
            }, on_conflict='user_id,machine_id').execute()
            
            return server
            
        except Exception as e:
            print(f"❌ Failed to connect to {resource.name}: {e}")
            
            # Mark server as offline
            self.supabase.table('servers').upsert({
                'user_id': user_id,
                'machine_id': machine_id,
                'name': resource.name,
                'status': 'offline',
                'last_seen_at': datetime.utcnow().isoformat()
            }, on_conflict='user_id,machine_id').execute()
            
            return None
    
    def get_connection_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get connection performance stats for all user's servers.
        
        Returns:
            Dict with server connection stats
        """
        try:
            result = self.supabase.table('servers')\
                .select('name, status, connection_latency_ms, connection_tested_at, preferred_connection_url')\
                .eq('user_id', user_id)\
                .execute()
            
            servers = result.data or []
            
            stats = {
                'total_servers': len(servers),
                'online': sum(1 for s in servers if s.get('status') == 'online'),
                'offline': sum(1 for s in servers if s.get('status') == 'offline'),
                'cached_connections': sum(1 for s in servers if s.get('preferred_connection_url')),
                'servers': []
            }
            
            for server in servers:
                stats['servers'].append({
                    'name': server.get('name'),
                    'status': server.get('status'),
                    'latency_ms': server.get('connection_latency_ms'),
                    'cached': bool(server.get('preferred_connection_url')),
                    'tested_at': server.get('connection_tested_at')
                })
            
            return stats
            
        except Exception as e:
            print(f"Error getting connection stats: {e}")
            return {}


async def get_plex_connection_manager(supabase: Client) -> PlexConnectionManager:
    """Dependency for getting connection manager."""
    return PlexConnectionManager(supabase)
