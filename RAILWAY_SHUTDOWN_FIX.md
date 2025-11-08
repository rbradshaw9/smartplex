# Railway Container Shutdown Issue - Diagnosis & Fix

## What's Happening

Your logs show:
```
✅ API starts successfully
✅ All environment variables are SET
✅ Uvicorn running on http://0.0.0.0:8080
❌ But then immediately: "Shutting down"
```

This means Railway is **stopping the container on purpose**, not a crash.

---

## Possible Causes & Solutions

### 1. Health Check Failure (MOST LIKELY)

Railway might be trying to health check your app but failing.

**Check in Railway Dashboard:**
1. Go to your API service
2. Click on "Settings" tab
3. Look for "Health Check" section
4. See if there's a health check path configured

**Solution A - Set correct health check:**
- Health Check Path: `/health`
- Health Check Timeout: `30` seconds

**Solution B - Disable health check temporarily:**
- Remove any health check configuration
- Let Railway use default behavior

---

### 2. No Active Deployment Selected

Railway might have multiple deployments and none is "active".

**Check:**
1. Railway dashboard → API service → "Deployments" tab
2. Look at the latest deployment
3. Check if it says "Active" or "Removed"

**If it says "Removed":**
- Click the three dots menu
- Click "Redeploy"
- Or click "Set as Active"

---

### 3. Port Binding Issue

Your logs show `http://0.0.0.0:8080` but Railway might expect a different port.

**Check Railway Settings:**
1. Settings tab → look for "PORT" variable
2. Should be automatically set by Railway

**Fix if needed:**
- Railway should automatically set `$PORT` environment variable
- Our start command uses `--port $PORT` which should work
- Verify Railway isn't overriding this

---

### 4. Deployment Being Replaced

If you just pushed code, Railway might be:
1. Starting the old deployment (what you see in logs)
2. Shutting it down
3. Starting the new deployment

**What to do:**
- Wait 2-3 minutes for new deployment to complete
- Refresh the logs
- Look for the new deployment's logs

---

## Quick Diagnostic Steps

### Step 1: Check Current Deployment Status

1. Railway dashboard → API service
2. Deployments tab
3. Look at the top deployment - is it:
   - ✅ "Active" and green?
   - ⚠️ "Building" or "Deploying"?
   - ❌ "Failed" or "Removed"?

### Step 2: Check for Active Requests

Try accessing your API directly:

```bash
# Test health endpoint
curl https://smartplex-production.up.railway.app/health
```

**If you get:**
- ✅ `{"status":"healthy"}` - API is running! Just logs are old
- ❌ `Connection refused` - Container is actually down
- ❌ `502 Bad Gateway` - Railway can't reach your container

### Step 3: Check Health Check Settings

1. Railway → API service → Settings
2. Scroll to "Health Check"
3. Check configuration

**Recommended settings:**
```
Health Check Path: /health
Health Check Interval: 60 seconds
Health Check Timeout: 30 seconds
```

### Step 4: Force Redeploy

1. Deployments tab → Latest deployment
2. Three dots menu → "Redeploy"
3. Wait for new deployment
4. Check logs again

---

## What Success Looks Like

When working correctly, logs should show:

```
🚀 SmartPlex API starting up...
🔧 Environment: production
🔗 Supabase URL: https://qqqyzrvwysxuevg8ww.supabase.co
🔑 Supabase Service Key: SET
🌐 Frontend URL: https://smartplex-ecru.vercel.app
🔒 CORS allowed origins: [...]
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080

[then NO shutdown message until you deploy again]
```

The logs should stay running and you should see:
- Health check requests: `GET /health` every minute
- Your actual API requests when you use the app

---

## CRITICAL: Find Your Railway URL First!

The logs show your API is starting, but we need to find the correct Railway URL.

### How to Find Your Railway URL:

1. **Go to Railway Dashboard** → Your project → API service
2. **Click on "Settings" tab**
3. **Scroll to "Networking" or "Domains" section**
4. **Look for "Public Networking" or "Generate Domain"**

You should see something like:
- `your-app-name.up.railway.app` 
- Or a custom domain if you configured one

### Generate a Domain if Missing:

If you don't see a domain:
1. Settings → Networking/Domains section
2. Click "Generate Domain" or "Add Domain"
3. Railway will create a domain like `your-service-123abc.up.railway.app`
4. **This is your API URL!**

### Update Environment Variables:

Once you have the correct Railway URL:

1. **Update Vercel** (Frontend):
   - Vercel dashboard → Environment Variables
   - `NEXT_PUBLIC_API_URL` = `https://YOUR-ACTUAL-RAILWAY-URL.up.railway.app`
   - Redeploy frontend

2. **Update Railway** (Backend):
   - Railway dashboard → Variables
   - Verify `FRONTEND_URL` is still correct
   - Should be: `https://smartplex-ecru.vercel.app`

### Test with Correct URL:

```bash
# Replace with your actual Railway URL
curl https://YOUR-ACTUAL-URL.up.railway.app/health
```

## Most Likely Fix

**The "smartplex-production" URL doesn't exist!** 

Railway generates URLs based on:
- Your service name (might not match project name)
- Or you need to generate a domain first

**Action Steps:**
1. ✅ Find the real Railway URL in Settings → Networking
2. ✅ Generate domain if none exists
3. ✅ Test it with curl
4. ✅ Update Vercel environment variable with correct URL
5. ✅ Redeploy frontend

---

## Additional Checks

### Is the API actually running?

Even if logs show shutdown, the API might still be running. Test it:

```bash
# Test health
curl https://smartplex-production.up.railway.app/health

# Test root endpoint
curl https://smartplex-production.up.railway.app/

# Test CORS preflight
curl -X OPTIONS https://smartplex-production.up.railway.app/api/auth/plex/login \
  -H "Origin: https://smartplex-ecru.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

**If any of these work**, your API is running fine! The logs you saw were from a previous deployment being shut down.

---

## Contact Railway Support

If none of this works, you might need Railway support:

1. Railway dashboard → "?" icon (bottom left)
2. "Contact Support"
3. Include:
   - Your project name
   - Service name (API)
   - The logs you shared
   - That environment variables are set correctly
   - That the API starts but immediately shuts down

---

## Next Steps

1. ✅ Try accessing the API with curl commands above
2. ✅ Check if latest deployment is "Active"
3. ✅ Configure health check to `/health`
4. ✅ Force redeploy if needed
5. ✅ If API responds to curl, proceed to fix the frontend URL issue in Vercel
