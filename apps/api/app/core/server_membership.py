"""
Helper functions for multi-tenancy and server membership.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from supabase import Client
import logging

logger = logging.getLogger(__name__)


async def get_user_primary_server(supabase: Client, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the primary server for a user.
    
    Priority:
    1. Server where user is owner
    2. Most recently accessed server
    3. First server alphabetically
    
    Args:
        supabase: Supabase client
        user_id: User's UUID
        
    Returns:
        Server record or None if user has no servers
    """
    try:
        # Query server_members to find user's servers
        result = supabase.table('server_members')\
            .select('server_id, role, last_accessed_at, servers(*)')\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            logger.warning(f"User {user_id} has no active server memberships")
            return None
        
        memberships = result.data
        
        # Priority 1: Find server where user is owner
        for membership in memberships:
            if membership.get('role') == 'owner' and membership.get('servers'):
                logger.info(f"Using owned server for user {user_id}")
                return membership['servers']
        
        # Priority 2: Most recently accessed
        sorted_by_access = sorted(
            [m for m in memberships if m.get('last_accessed_at')],
            key=lambda m: m['last_accessed_at'],
            reverse=True
        )
        if sorted_by_access and sorted_by_access[0].get('servers'):
            logger.info(f"Using recently accessed server for user {user_id}")
            return sorted_by_access[0]['servers']
        
        # Priority 3: First server alphabetically (fallback)
        if memberships[0].get('servers'):
            logger.info(f"Using first available server for user {user_id}")
            return memberships[0]['servers']
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting primary server for user {user_id}: {e}")
        return None


async def get_server_admin(supabase: Client, server_id: str) -> Optional[str]:
    """
    Get the admin/owner user_id for a server.
    
    Args:
        supabase: Supabase client
        server_id: Server UUID
        
    Returns:
        Admin user_id or None
    """
    try:
        # First try to get owner from servers table
        server_result = supabase.table('servers')\
            .select('user_id')\
            .eq('id', server_id)\
            .single()\
            .execute()
        
        if server_result.data:
            return server_result.data['user_id']
        
        # Fallback: get owner from server_members
        member_result = supabase.table('server_members')\
            .select('user_id')\
            .eq('server_id', server_id)\
            .eq('role', 'owner')\
            .single()\
            .execute()
        
        return member_result.data['user_id'] if member_result.data else None
        
    except Exception as e:
        logger.error(f"Error getting admin for server {server_id}: {e}")
        return None


async def has_server_access(supabase: Client, user_id: str, server_id: str) -> bool:
    """
    Check if a user has access to a server.
    
    Args:
        supabase: Supabase client
        user_id: User UUID
        server_id: Server UUID
        
    Returns:
        True if user has active access
    """
    try:
        result = supabase.table('server_members')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('server_id', server_id)\
            .eq('is_active', True)\
            .limit(1)\
            .execute()
        
        return bool(result.data)
        
    except Exception as e:
        logger.error(f"Error checking server access: {e}")
        return False
