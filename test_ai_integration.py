"""
Test script for AI integration endpoints.
Run this after deploying to verify AI features work correctly.
"""

import httpx
import asyncio
import json
from datetime import datetime


# Update these with your actual values
BASE_URL = "https://smartplex-api.up.railway.app"  # Your Railway backend URL
PLEX_TOKEN = "YOUR_PLEX_TOKEN_HERE"  # Get from localStorage after login
USER_EMAIL = "rbradshaw@gmail.com"


async def test_ai_chat():
    """Test AI chat endpoint."""
    print("\n🤖 Testing AI Chat...")
    
    async with httpx.AsyncClient() as client:
        # First, authenticate to get session
        auth_response = await client.post(
            f"{BASE_URL}/api/auth/plex/login",
            json={"plex_token": PLEX_TOKEN, "email": USER_EMAIL}
        )
        
        if auth_response.status_code != 200:
            print(f"❌ Auth failed: {auth_response.text}")
            return
        
        session_data = auth_response.json()
        print(f"✅ Authenticated as {session_data['user']['email']}")
        
        # Test chat
        chat_response = await client.post(
            f"{BASE_URL}/api/ai/chat",
            json={
                "message": "What kind of movies do I like based on my watch history?"
            },
            headers={"Authorization": f"Bearer {session_data['supabase_session']['access_token']}"}
        )
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"✅ Chat response: {chat_data['response'][:100]}...")
            print(f"   Tokens used: {chat_data.get('tokens_used', 0)}")
            print(f"   Model: {chat_data.get('model_used', 'unknown')}")
        else:
            print(f"❌ Chat failed: {chat_response.text}")


async def test_ai_analysis():
    """Test AI viewing pattern analysis."""
    print("\n📊 Testing AI Analysis...")
    
    async with httpx.AsyncClient() as client:
        # Authenticate
        auth_response = await client.post(
            f"{BASE_URL}/api/auth/plex/login",
            json={"plex_token": PLEX_TOKEN, "email": USER_EMAIL}
        )
        
        if auth_response.status_code != 200:
            print(f"❌ Auth failed")
            return
        
        session_data = auth_response.json()
        
        # Test analysis
        analysis_response = await client.post(
            f"{BASE_URL}/api/ai/analyze",
            json={
                "time_period": "30d",
                "include_recommendations": True
            },
            headers={"Authorization": f"Bearer {session_data['supabase_session']['access_token']}"}
        )
        
        if analysis_response.status_code == 200:
            analysis = analysis_response.json()
            print(f"✅ Analysis summary: {analysis['summary']}")
            print(f"\n   📈 Insights:")
            for insight in analysis.get('insights', [])[:3]:
                print(f"      - {insight}")
            print(f"\n   📊 Statistics:")
            stats = analysis.get('statistics', {})
            print(f"      - Total watched: {stats.get('total_items_watched', 0)} items")
            print(f"      - Total hours: {stats.get('total_hours', 0)} hours")
            print(f"\n   🎬 Recommendations:")
            for rec in analysis.get('recommendations', [])[:3]:
                print(f"      - {rec.get('title')} ({rec.get('year', 'N/A')}): {rec.get('reason', 'N/A')[:60]}...")
        else:
            print(f"❌ Analysis failed: {analysis_response.text}")


async def test_ai_recommendations():
    """Test AI recommendations endpoint."""
    print("\n🎯 Testing AI Recommendations...")
    
    async with httpx.AsyncClient() as client:
        # Authenticate
        auth_response = await client.post(
            f"{BASE_URL}/api/auth/plex/login",
            json={"plex_token": PLEX_TOKEN, "email": USER_EMAIL}
        )
        
        if auth_response.status_code != 200:
            print(f"❌ Auth failed")
            return
        
        session_data = auth_response.json()
        
        # Test recommendations
        rec_response = await client.get(
            f"{BASE_URL}/api/ai/recommendations?limit=5",
            headers={"Authorization": f"Bearer {session_data['supabase_session']['access_token']}"}
        )
        
        if rec_response.status_code == 200:
            recommendations = rec_response.json()
            print(f"✅ Got {len(recommendations)} recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n   {i}. {rec.get('title')} ({rec.get('type', 'unknown')})")
                print(f"      Year: {rec.get('year', 'N/A')}")
                print(f"      Reason: {rec.get('reason', 'N/A')[:80]}...")
                print(f"      Confidence: {rec.get('confidence', 0):.2f}")
        else:
            print(f"❌ Recommendations failed: {rec_response.text}")


async def test_plex_cache():
    """Test Plex data caching."""
    print("\n⚡ Testing Plex Cache...")
    
    async with httpx.AsyncClient() as client:
        # First request (should fetch from Plex)
        print("   Making first request (will fetch from Plex)...")
        start = datetime.now()
        
        response1 = await client.get(
            f"{BASE_URL}/api/plex/watch-history?plex_token={PLEX_TOKEN}&limit=20"
        )
        
        duration1 = (datetime.now() - start).total_seconds()
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"   ✅ First request: {duration1:.2f}s")
            print(f"      From cache: {data1.get('from_cache', False)}")
            print(f"      Items: {len(data1.get('watch_history', []))}")
            
            # Second request (should be cached)
            print("\n   Making second request (should be cached)...")
            start = datetime.now()
            
            response2 = await client.get(
                f"{BASE_URL}/api/plex/watch-history?plex_token={PLEX_TOKEN}&limit=20"
            )
            
            duration2 = (datetime.now() - start).total_seconds()
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"   ✅ Second request: {duration2:.2f}s")
                print(f"      From cache: {data2.get('from_cache', False)}")
                print(f"      Speedup: {duration1/duration2:.1f}x faster")
                
                if data2.get('sync_info'):
                    sync = data2['sync_info']
                    print(f"\n   📅 Last sync:")
                    print(f"      Time: {sync.get('last_sync_at')}")
                    print(f"      Processed: {sync.get('items_processed', 0)} items")
        else:
            print(f"❌ Cache test failed: {response1.text}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 SmartPlex AI Integration Tests")
    print("=" * 60)
    
    if PLEX_TOKEN == "YOUR_PLEX_TOKEN_HERE":
        print("\n❌ Please update PLEX_TOKEN in this script first!")
        print("   Get it from your browser localStorage after logging in")
        return
    
    try:
        # Test cache first (no auth required)
        await test_plex_cache()
        
        # Test AI endpoints (require auth)
        await test_ai_chat()
        await test_ai_analysis()
        await test_ai_recommendations()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
