#!/bin/bash

# Railway Deployment Status Checker
# Run this to check if Railway deployment is working

echo "🔍 Checking Railway Deployment Status..."
echo ""

API_URL="https://smartplexapi-production.up.railway.app"

echo "1️⃣  Testing root endpoint..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/" 2>&1)
if [ "$RESPONSE" = "200" ]; then
    echo "✅ Root endpoint responding (200 OK)"
    curl -s "$API_URL/" | python3 -m json.tool 2>/dev/null || echo "Response: $(curl -s $API_URL/)"
else
    echo "❌ Root endpoint failed (HTTP $RESPONSE)"
fi

echo ""
echo "2️⃣  Testing health endpoint (with slash)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/" 2>&1)
if [ "$RESPONSE" = "200" ]; then
    echo "✅ Health endpoint responding (200 OK)"
    curl -s "$API_URL/health/" | python3 -m json.tool 2>/dev/null
else
    echo "❌ Health endpoint failed (HTTP $RESPONSE)"
fi

echo ""
echo "3️⃣  Testing CORS headers..."
curl -s -I -X OPTIONS "$API_URL/api/auth/plex/login" \
  -H "Origin: https://smartplex-ecru.vercel.app" \
  -H "Access-Control-Request-Method: POST" 2>&1 | grep -i "access-control"

echo ""
echo "4️⃣  Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$RESPONSE" = "200" ]; then
    echo "✅ API is UP and responding"
    echo "✅ Latest deployment is active"
    echo ""
    echo "Next step: Update Vercel environment variable"
    echo "  NEXT_PUBLIC_API_URL = https://smartplexapi-production.up.railway.app"
else
    echo "❌ API is DOWN or not responding"
    echo ""
    echo "Action required:"
    echo "  1. Check Railway dashboard → Deployments"
    echo "  2. Verify latest deployment is 'Active'"
    echo "  3. Check health check path is /health/ (with slash)"
    echo "  4. Check logs for 'Stopping Container' message"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
