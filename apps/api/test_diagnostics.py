#!/usr/bin/env python3
"""
Test script to verify Plex authentication flow and diagnose issues.
"""

import os
import sys
import httpx
import asyncio
from typing import Optional


def test_environment_variables():
    """Check if required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL"),
        "SMARTPLEX_ENV": os.getenv("SMARTPLEX_ENV", "development"),
    }
    
    all_set = True
    for var, value in required_vars.items():
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var:
                display_value = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_set = False
    
    return all_set


async def test_plex_token(token: str):
    """Test if a Plex token is valid."""
    print(f"\n🔐 Testing Plex token (length: {len(token)})...")
    
    headers = {
        'X-Plex-Token': token,
        'X-Plex-Product': 'SmartPlex',
        'X-Plex-Client-Identifier': 'smartplex-auth',
        'Accept': 'application/json'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://plex.tv/users/account.json',
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user = user_data.get('user', {})
                print(f"  ✅ Token valid!")
                print(f"  👤 Username: {user.get('username')}")
                print(f"  📧 Email: {user.get('email')}")
                print(f"  🆔 Plex ID: {user.get('id')}")
                return True
            else:
                print(f"  ❌ Token invalid: {response.status_code}")
                print(f"  📋 Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"  ❌ Error testing token: {e}")
        return False


async def test_supabase_connection():
    """Test if Supabase connection works."""
    print("\n🔗 Testing Supabase connection...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("  ❌ Missing Supabase credentials")
        return False
    
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        
        # Try to query users table
        result = client.table('users').select('id').limit(1).execute()
        print(f"  ✅ Supabase connection successful!")
        print(f"  📊 Users table exists: {len(result.data) >= 0}")
        return True
        
    except Exception as e:
        print(f"  ❌ Supabase connection failed: {e}")
        return False


async def test_api_endpoint(api_url: str):
    """Test if the API endpoint is reachable."""
    print(f"\n🌐 Testing API endpoint: {api_url}...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            response = await client.get(f"{api_url}/health", timeout=10.0)
            if response.status_code == 200:
                print(f"  ✅ API is healthy!")
                data = response.json()
                print(f"  📋 Response: {data}")
                return True
            else:
                print(f"  ❌ API returned {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print(f"  ❌ Cannot connect to API (connection refused)")
        return False
    except Exception as e:
        print(f"  ❌ Error testing API: {e}")
        return False


async def test_cors(api_url: str, frontend_url: str):
    """Test if CORS is configured correctly."""
    print(f"\n🔒 Testing CORS configuration...")
    print(f"  Frontend: {frontend_url}")
    print(f"  API: {api_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.options(
                f"{api_url}/api/auth/plex/login",
                headers={
                    "Origin": frontend_url,
                    "Access-Control-Request-Method": "POST",
                },
                timeout=10.0
            )
            
            headers = response.headers
            allow_origin = headers.get("access-control-allow-origin", "")
            allow_methods = headers.get("access-control-allow-methods", "")
            
            if frontend_url in allow_origin or "*" in allow_origin:
                print(f"  ✅ CORS allows origin: {allow_origin}")
            else:
                print(f"  ❌ CORS blocks origin. Allowed: {allow_origin}")
            
            if "POST" in allow_methods:
                print(f"  ✅ CORS allows POST")
            else:
                print(f"  ❌ CORS blocks POST. Allowed: {allow_methods}")
            
            return "POST" in allow_methods and (frontend_url in allow_origin or "*" in allow_origin)
            
    except Exception as e:
        print(f"  ❌ Error testing CORS: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 SmartPlex Backend Diagnostics")
    print("=" * 60)
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test Supabase connection (if env vars are set)
    if env_ok:
        await test_supabase_connection()
    
    # Test API endpoint
    api_url = os.getenv("API_URL", "https://smartplex-production.up.railway.app")
    api_ok = await test_api_endpoint(api_url)
    
    # Test CORS
    if api_ok:
        frontend_url = os.getenv("FRONTEND_URL", "https://smartplex-ecru.vercel.app")
        await test_cors(api_url, frontend_url)
    
    # If user provides a Plex token, test it
    if len(sys.argv) > 1:
        plex_token = sys.argv[1]
        await test_plex_token(plex_token)
    
    print("\n" + "=" * 60)
    print("✅ Diagnostics complete!")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
