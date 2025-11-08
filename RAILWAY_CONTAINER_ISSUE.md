# 🚨 IMMEDIATE ISSUE: Railway Container Keeps Stopping!

## The Problem

Looking at the logs:
```
2025-11-08T15:36:06 Starting Container
2025-11-08T15:36:06 🚀 SmartPlex API starting up...
2025-11-08T15:36:07 Stopping Container  ← 1 second later!!!
```

**The container is being killed IMMEDIATELY after starting!**

This is why you're getting 500 errors - Railway starts the container, but then immediately stops it before it can handle any requests.

---

## Why This Happens

Railway stops containers when:

1. **❌ Health check fails** - Railway pings an endpoint, gets no response, kills it
2. **❌ No active deployment** - Multiple deployments exist, wrong one is "active"
3. **❌ Port binding issue** - App isn't listening on the right port
4. **❌ Crash during startup** - App crashes before Railway marks it as "ready"
5. **❌ Resource limits exceeded** - Out of memory/CPU

---

## Diagnosis Steps

### 1. Check Railway Deployment Status

Go to Railway dashboard and check:

**Deployments Tab:**
- Is the LATEST deployment marked as "Active"? ✅ or ❌
- Are there multiple deployments showing?
- Does it say "Crashed", "Removed", or "Failed"?

**If multiple deployments:**
- Railway might be cycling between them
- Click the latest → "Set as Active"

### 2. Check Railway Service Settings

**Settings → Networking:**
- Is a domain generated?
- Does it show "Service is Online" or "Service is Offline"?

**Settings → Health Check:**
- Is there a health check path configured?
- If YES: Is it `/health` or `/health/`? (the slash matters!)
- **PROBLEM:** Our health endpoint is at `/health/` but Railway might be checking `/health`

### 3. Check Port Configuration

**Settings → Variables:**
- Is there a `PORT` variable?
- Railway should auto-inject this
- Our start command uses `--port $PORT` which should work

---

## Quick Fixes to Try

### Fix 1: Update Health Check Path

1. Railway → API Service → Settings
2. Scroll to "Health Check" section
3. Set:
   - **Path:** `/health/` (with trailing slash!)
   - **Timeout:** 30 seconds
   - **Interval:** 60 seconds
4. Save changes
5. Redeploy

### Fix 2: Disable Health Check Temporarily

1. Settings → Health Check
2. Remove/disable the health check path
3. Save
4. Redeploy
5. See if container stays up

### Fix 3: Force Redeploy Latest

1. Deployments tab
2. Find the VERY LATEST deployment (just pushed)
3. Three dots → "Redeploy"
4. Wait 3-4 minutes for full deployment
5. Check logs again

### Fix 4: Check Resource Usage

1. Click on the deployment
2. Look at "Metrics" or "Resources"
3. Check if Memory or CPU spiked then crashed

---

## What to Look For in Next Logs

**Good deployment looks like:**
```
Starting Container
🚀 SmartPlex API starting up...
🔧 Environment: production
🔗 Supabase URL: https://...
🔑 Supabase Service Key: SET
🌐 Frontend URL: https://...
🔒 CORS allowed origins: [...]
🔗 Initializing Supabase client...
✅ Supabase client initialized
INFO: Uvicorn running on http://0.0.0.0:8080
[STAYS RUNNING - no "Stopping Container" message]
INFO: 100.64.0.2:12345 - "GET /health/ HTTP/1.1" 200 OK
```

**Bad deployment:**
```
Starting Container
🚀 SmartPlex API starting up...
Stopping Container  ← Too fast!
```

---

## Most Likely Root Cause

Based on the pattern, **it's almost certainly a health check issue:**

Railway is trying to check `/health` but our endpoint is `/health/` (with trailing slash).

When the health check fails, Railway assumes the app is broken and stops it.

---

## Immediate Actions

1. ✅ **Code is now pushed** with lru_cache fix
2. ⏱️ **Wait 3-4 minutes** for Railway to finish deploying
3. 🔍 **Check deployment status** - is it "Active"?
4. 🏥 **Fix health check path** to `/health/` in Railway settings
5. 🔄 **Watch new logs** for "Stopping Container" - should NOT appear!

---

## Test After Deployment

Once container stays up (no "Stopping" message):

```bash
# Test if API is actually responding
curl https://smartplexapi-production.up.railway.app/

# Test health endpoint
curl https://smartplexapi-production.up.railway.app/health/

# Try authentication
# Open browser and test Plex login
```

---

## If Container Still Stops

If it STILL stops after these fixes:

1. **Check Railway logs for error messages** before it stops
2. **Contact Railway support** - might be a platform issue
3. **Try deploying to a new service** - current one might be in bad state
4. **Check Railway status page** - might be a broader outage

---

## Summary

**Problem:** Railway kills container 1 second after start  
**Why:** Likely health check failure  
**Fix:** Configure health check to `/health/` in Railway settings  
**Status:** Waiting for latest deployment with lru_cache fixes

The authentication error (`TypeError: unhashable type`) is now fixed in the code, but we need the container to stay alive first!
