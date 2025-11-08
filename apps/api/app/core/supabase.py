"""
Supabase client management for SmartPlex API.
Provides typed database client and authentication helpers.
"""

from typing import Any, Dict, Optional

from supabase import Client, create_client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings, Settings
from app.core.exceptions import AuthenticationException, DatabaseException

# HTTPBearer security scheme for JWT tokens
security = HTTPBearer()

# Singleton Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    """Get cached Supabase client instance (singleton pattern)."""
    global _supabase_client
    
    if _supabase_client is None:
        try:
            print("🔗 Initializing Supabase client...")
            _supabase_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_key,
            )
            print("✅ Supabase client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            raise DatabaseException(
                message="Failed to initialize Supabase client",
                details=str(e)
            )
    
    return _supabase_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: JWT token from Authorization header
        supabase: Supabase client instance
        
    Returns:
        User data from Supabase auth
        
    Raises:
        AuthenticationException: If token is invalid or user not found
    """
    try:
        # Verify JWT token with Supabase
        response = supabase.auth.get_user(credentials.credentials)
        
        if not response.user:
            raise AuthenticationException(
                message="Invalid or expired token",
                details="User not found in token"
            )
            
        return {
            "id": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata,
            "app_metadata": response.user.app_metadata,
        }
        
    except Exception as e:
        if isinstance(e, AuthenticationException):
            raise
        raise AuthenticationException(
            message="Failed to authenticate user",
            details=str(e)
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for optional authentication endpoints.
    """
    if not credentials:
        return None
        
    try:
        return await get_current_user(credentials, supabase)
    except AuthenticationException:
        return None