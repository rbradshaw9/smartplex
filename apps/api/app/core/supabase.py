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
from app.core.logging import get_logger

# HTTPBearer security scheme for JWT tokens
security = HTTPBearer()

# Singleton Supabase client instance
_supabase_client: Optional[Client] = None

# Logger
logger = get_logger("supabase")


def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    """Get cached Supabase client instance (singleton pattern)."""
    global _supabase_client
    
    if _supabase_client is None:
        try:
            print("🔗 Initializing Supabase client...")
            print(f"🔍 Supabase URL: {settings.supabase_url}")
            print(f"🔍 Service Key length: {len(settings.supabase_service_key)}")
            # Simple initialization without extra parameters
            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            print("✅ Supabase client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise DatabaseException(
                message="Database connection failed",
                details=str(e) if settings.environment == "development" else None
            )
    
    return _supabase_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    Fetches user role and metadata from the database.
    
    Args:
        credentials: JWT token from Authorization header
        supabase: Supabase client instance
        
    Returns:
        User data including role from database
        
    Raises:
        AuthenticationException: If token is invalid or user not found
    """
    try:
        # Verify JWT token with Supabase
        response = supabase.auth.get_user(credentials.credentials)
        
        if not response or not response.user:  # type: ignore
            raise AuthenticationException(
                message="Invalid or expired token",
                details="User not found in token"
            )
        
        # Fetch user record from database to get role
        user_data = supabase.table("users").select("*").eq("id", response.user.id).execute()
        
        if not user_data.data or len(user_data.data) == 0:
            # User authenticated but not in our database yet - create user record
            logger.warning(f"User {response.user.id} authenticated but not in database, creating record")
            new_user = {
                "id": response.user.id,
                "email": response.user.email,
                "display_name": response.user.user_metadata.get("full_name") or response.user.user_metadata.get("name"),
                "avatar_url": response.user.user_metadata.get("avatar_url"),
                "plex_user_id": response.user.user_metadata.get("plex_user_id"),
                "plex_username": response.user.user_metadata.get("plex_username"),
                "role": "user",  # Default role
            }
            supabase.table("users").insert(new_user).execute()
            user_record = new_user
        else:
            user_record = user_data.data[0]
            
        return {
            "id": response.user.id,
            "email": response.user.email,
            "role": user_record.get("role", "user"),
            "display_name": user_record.get("display_name"),
            "avatar_url": user_record.get("avatar_url"),
            "user_metadata": response.user.user_metadata,
            "app_metadata": response.user.app_metadata,
        }
        
    except Exception as e:
        if isinstance(e, AuthenticationException):
            raise
        logger.error(f"Authentication error: {e}")
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


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency that requires the current user to have admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User data if admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user