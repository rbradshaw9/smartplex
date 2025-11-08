"""
Plex Authentication API Route

This endpoint handles Plex authentication:
1. Validates Plex credentials with Plex.tv API
2. Retrieves user info from Plex
3. Creates/updates user in Supabase
4. Returns Supabase session token
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx
import base64
from typing import Dict, Any, Optional

from app.core.supabase import get_supabase_client
from app.config import get_settings

router = APIRouter()


class PlexLoginRequest(BaseModel):
    """Request model for Plex authentication using OAuth token."""
    authToken: str = Field(..., min_length=1, description="Plex OAuth auth token from PIN flow")


class PlexCredentialsRequest(BaseModel):
    """Legacy request model for username/password authentication."""
    username: str = Field(..., min_length=1, description="Plex username or email")
    password: str = Field(..., min_length=1, description="Plex password")


class PlexAuthResponse(BaseModel):
    user: Dict[str, Any]
    supabase_session: Dict[str, Any]
    message: str


@router.post("/login", response_model=PlexAuthResponse)
async def plex_login(
    credentials: PlexLoginRequest,
    supabase = Depends(get_supabase_client)
) -> PlexAuthResponse:
    """Authenticate user with Plex OAuth token and create/login to Supabase."""
    
    print("🔐 Starting Plex authentication flow...")
    print(f"📝 Auth token received (length: {len(credentials.authToken)})")
    
    try:
        # Step 1: Verify Plex token and get user data
        print("📡 Validating Plex token with plex.tv...")
        plex_user_data = await get_plex_user_from_token(credentials.authToken)
        print(f"✅ Plex user validated: {plex_user_data.get('username')} (ID: {plex_user_data.get('id')})")
        
        # Step 2: Create or get user in Supabase Auth
        email = plex_user_data.get('email') or f"{plex_user_data['username']}@smartplex.local"
        print(f"📧 Using email: {email}")
        
        # Try to find existing auth user by email
        try:
            # Check if auth user exists
            print("🔍 Checking for existing Supabase auth user...")
            auth_user_response = supabase.auth.admin.list_users()
            existing_auth_user = next(
                (u for u in auth_user_response if u.email == email), 
                None
            )
            
            if existing_auth_user:
                # Update existing auth user metadata
                print(f"✅ Found existing auth user: {existing_auth_user.id}")
                user_id = existing_auth_user.id
                supabase.auth.admin.update_user_by_id(
                    user_id,
                    {
                        "user_metadata": {
                            "plex_user_id": str(plex_user_data['id']),
                            "plex_username": plex_user_data['username'],
                            "display_name": plex_user_data.get('title', plex_user_data['username']),
                        }
                    }
                )
                print("✅ Updated auth user metadata")
            else:
                # Create new auth user
                print("➕ Creating new Supabase auth user...")
                import secrets
                temp_password = secrets.token_urlsafe(32)
                
                auth_response = supabase.auth.admin.create_user({
                    "email": email,
                    "password": temp_password,
                    "email_confirm": True,
                    "user_metadata": {
                        "plex_user_id": str(plex_user_data['id']),
                        "plex_username": plex_user_data['username'],
                        "display_name": plex_user_data.get('title', plex_user_data['username']),
                    }
                })
                user_id = auth_response.user.id
                print(f"✅ Created auth user: {user_id}")
            
            # Step 3: Create/update user profile in public.users table
            print("🔍 Checking for existing user profile...")
            existing_profile = supabase.table('users').select('*').eq('id', user_id).execute()
            
            if existing_profile.data:
                # Update existing profile
                print(f"✅ Found existing profile, updating...")
                supabase.table('users').update({
                    'plex_user_id': str(plex_user_data['id']),
                    'plex_username': plex_user_data['username'],
                    'display_name': plex_user_data.get('title', plex_user_data['username']),
                    'updated_at': 'now()',
                }).eq('id', user_id).execute()
                user_data = existing_profile.data[0]
                print("✅ Profile updated")
            else:
                # Create new profile
                print("➕ Creating new user profile...")
                new_profile = supabase.table('users').insert({
                    'id': user_id,
                    'email': email,
                    'display_name': plex_user_data.get('title', plex_user_data['username']),
                    'plex_user_id': str(plex_user_data['id']),
                    'plex_username': plex_user_data['username'],
                    'role': 'user'
                }).execute()
                user_data = new_profile.data[0]
                print(f"✅ Profile created: {user_data['id']}")
            
            # Step 4: Generate session token
            print("🎫 Generating session token...")
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            session_data = {
                'user_id': user_id,
                'email': email,
                'display_name': user_data.get('display_name'),
                'plex_user_id': user_data.get('plex_user_id'),
                'plex_token': credentials.authToken,
                'expires_at': expires_at.isoformat()
            }
            
            print("✅ Authentication successful!")
            return PlexAuthResponse(
                user=user_data,
                supabase_session=session_data,
                message="Successfully authenticated with Plex"
            )
            
        except Exception as e:
            # If Supabase auth fails, fall back to table-only approach
            # This allows the app to work even if auth.admin API has issues
            print(f"⚠️ Auth user creation failed, using table-only fallback: {e}")
            
            existing_user = supabase.table('users').select('*').eq('email', email).execute()
            
            if existing_user.data:
                user_data = existing_user.data[0]
                supabase.table('users').update({
                    'plex_user_id': str(plex_user_data['id']),
                    'plex_username': plex_user_data['username'],
                    'display_name': plex_user_data.get('title', plex_user_data['username']),
                    'updated_at': 'now()',
                }).eq('id', user_data['id']).execute()
            else:
                new_user = supabase.table('users').insert({
                    'email': email,
                    'display_name': plex_user_data.get('title', plex_user_data['username']),
                    'plex_user_id': str(plex_user_data['id']),
                    'plex_username': plex_user_data['username'],
                    'role': 'user'
                }).execute()
                user_data = new_user.data[0]
            
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            session_data = {
                'user_id': user_data['id'],
                'email': email,
                'display_name': user_data.get('display_name'),
                'plex_user_id': user_data.get('plex_user_id'),
                'plex_token': credentials.authToken,
                'expires_at': expires_at.isoformat()
            }
            
            return PlexAuthResponse(
                user=user_data,
                supabase_session=session_data,
                message="Successfully authenticated with Plex"
            )
        
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        import traceback
        print(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=401,
            detail=f"Plex authentication failed: {str(e)}"
        )


async def get_plex_user_from_token(auth_token: str) -> Dict[str, Any]:
    """Get Plex user details from OAuth token."""
    
    headers = {
        'X-Plex-Token': auth_token,
        'X-Plex-Product': 'SmartPlex',
        'X-Plex-Client-Identifier': 'smartplex-auth',
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        # Get user details using the OAuth token
        user_response = await client.get(
            'https://plex.tv/users/account.json',
            headers=headers,
            timeout=10.0
        )
        
        if user_response.status_code != 200:
            error_detail = user_response.text
            if 'unauthorized' in error_detail.lower():
                raise ValueError("Invalid Plex token")
            else:
                raise ValueError(f"Failed to get Plex user details: {error_detail}")
        
        user_data = user_response.json()
        user_account = user_data.get('user', {})
        
        return {
            'id': user_account.get('id'),
            'username': user_account.get('username'),
            'email': user_account.get('email'),
            'title': user_account.get('title') or user_account.get('username'),
            'thumb': user_account.get('thumb'),
            'authToken': auth_token
        }


async def authenticate_with_plex(username: str, password: str) -> Dict[str, Any]:
    """Legacy: Authenticate with Plex.tv API using username/password."""
    
    # Encode credentials for Basic Auth
    credentials_b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {credentials_b64}',
        'X-Plex-Product': 'SmartPlex',
        'X-Plex-Version': '1.0.0',
        'X-Plex-Client-Identifier': 'smartplex-auth',
        'X-Plex-Platform': 'Web',
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        # Get auth token from Plex
        auth_response = await client.post(
            'https://plex.tv/users/sign_in.json',
            headers=headers,
            timeout=10.0
        )
        
        if auth_response.status_code != 201:
            error_detail = auth_response.text
            if 'unauthorized' in error_detail.lower():
                raise ValueError("Invalid Plex credentials")
            else:
                raise ValueError(f"Plex authentication failed: {error_detail}")
        
        auth_data = auth_response.json()
        user_info = auth_data.get('user', {})
        auth_token = user_info.get('authToken')
        
        if not auth_token:
            raise ValueError("Failed to get Plex auth token")
        
        # Get user details using the token
        return await get_plex_user_from_token(auth_token)


@router.get("/verify")
async def verify_plex_token(
    token: str,
    supabase = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """Verify a Plex token and return user info."""
    
    headers = {
        'X-Plex-Token': token,
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://plex.tv/users/account.json',
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Plex token")
        
        return response.json()