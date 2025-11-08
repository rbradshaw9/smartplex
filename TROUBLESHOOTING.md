# SmartPlex Troubleshooting Guide

## Current Issue: Plex Authentication Failing with 500 Error

### Observed Symptoms
- ✅ Plex authentication window opens successfully
- ✅ User authenticates in Plex and sees success
- ❌ Frontend shows spinning wheel (request hangs)
- ❌ Browser console shows CORS error
- ❌ Browser console shows 500 Internal Server Error on POST to `/api/auth/plex/login`
- ❌ API URL mismatch: using `smartplexapi-production.up.railway.app` instead of `smartplex-production.up.railway.app`

---

## Step-by-Step Troubleshooting

### 1. Check Railway Deployment Logs (CRITICAL)

The 500 error means the backend is crashing. We need to see the actual error:

**Steps:**
1. Go to Railway dashboard: https://railway.app/
2. Select your `smartplex` project
3. Click on the `api` service (or whatever you named it)
4. Click on the "Deployments" tab
5. Click on the latest deployment
6. Click "View Logs" button
7. **Look for Python stack traces** - these will show the actual error

**Common errors to look for:**
- `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings` - Missing environment variables
- `supabase.lib.client_options.ClientOptions` errors - Invalid Supabase credentials
- `KeyError: 'SUPABASE_SERVICE_KEY'` - Environment variable not set
- `AttributeError: 'NoneType'` - Supabase client not initialized properly

---

### 2. Verify Railway Environment Variables

**Required environment variables in Railway:**

| Variable | Value | Purpose |
|----------|-------|---------|
| `SMARTPLEX_ENV` | `production` | Sets production mode |
| `SUPABASE_URL` | `https://qqqyzrvwysxuevgsww.supabase.co` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | `eyJhbG...` (long JWT token) | Service role key for admin operations |
| `FRONTEND_URL` | `https://smartplex-ecru.vercel.app` | Frontend URL for CORS |

**How to check:**
1. Railway dashboard → Select project
2. Click on `api` service
3. Go to "Variables" tab
4. Verify all 4 variables are present and correct

**How to get SUPABASE_SERVICE_KEY:**
1. Go to Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to Settings → API
4. Copy the `service_role` key (NOT the `anon` key)
5. It should start with `eyJhbG...` and be very long

---

### 3. Fix Vercel Environment Variable (URL Mismatch)

**Problem:** Frontend is using wrong API URL (`smartplexapi-production` vs `smartplex-production`)

**Steps:**
1. Go to Vercel dashboard: https://vercel.com/
2. Select the `smartplex` project
3. Go to Settings → Environment Variables
4. Find `NEXT_PUBLIC_API_URL`
5. **Current (wrong) value:** `https://smartplexapi-production.up.railway.app`
6. **Correct value:** `https://smartplex-production.up.railway.app`
7. Update the value
8. Go to Deployments tab
9. Click "Redeploy" on the latest deployment (three dots menu → Redeploy)

**Note:** Environment variables in Next.js are baked into the build at build time. You MUST redeploy for changes to take effect.

---

### 4. Check Database Schema Deployment

The backend expects certain tables and functions to exist in Supabase.

**Steps:**
1. Go to Supabase dashboard
2. Select your project
3. Go to SQL Editor
4. Check if these tables exist by running:
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public'
   ORDER BY table_name;
   ```

**Expected tables:**
- `users`
- `servers`
- `integrations`
- `media_items`
- `user_stats`
- `cleanup_log`
- `sync_history`
- `chat_history`
- `agent_heartbeats`

**If tables are missing:**
1. Run `packages/db/schema.sql` in SQL Editor
2. Then run `packages/db/rls.sql` in SQL Editor
3. Wait 30 seconds for changes to propagate

---

### 5. Test API Endpoint Directly

Once Railway logs show no errors, test the API directly:

**Test health endpoint:**
```bash
curl https://smartplex-production.up.railway.app/health
```

Expected response:
```json
{"status": "healthy"}
```

**Test CORS headers:**
```bash
curl -X OPTIONS https://smartplex-production.up.railway.app/api/auth/plex/login \
  -H "Origin: https://smartplex-ecru.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

Look for these headers in response:
- `Access-Control-Allow-Origin: https://smartplex-ecru.vercel.app`
- `Access-Control-Allow-Methods: POST, OPTIONS`

---

### 6. Enable Debug Logging (if still failing)

If the issue persists, we can add detailed logging to see exactly what's happening:

1. Check the modified `plex_auth.py` file (see changes below)
2. Deploy changes to Railway (git push)
3. Retry authentication
4. Check Railway logs for detailed output

---

## Quick Diagnosis Checklist

Run through this checklist:

- [ ] **Railway logs show errors?** → Check environment variables
- [ ] **"ValidationError for Settings"?** → Missing `SUPABASE_SERVICE_KEY` or `SUPABASE_URL`
- [ ] **"Invalid Plex token"?** → Token expired (normal, try logging in again)
- [ ] **CORS error in browser?** → Wrong `FRONTEND_URL` in Railway or wrong `NEXT_PUBLIC_API_URL` in Vercel
- [ ] **404 error?** → Wrong API URL in frontend
- [ ] **Connection refused?** → API not running on Railway (check deployment status)
- [ ] **Database errors?** → Run schema.sql and rls.sql in Supabase

---

## Expected Successful Flow

When everything works:

1. **Frontend:** User clicks "Sign in with Plex"
2. **Frontend:** Calls Plex API to generate PIN → Gets PIN and polling ID
3. **Frontend:** Opens `plex.tv/link` with PIN in popup window
4. **User:** Enters PIN in Plex window → Plex returns auth token
5. **Frontend:** Polls Plex API every 2 seconds with polling ID
6. **Frontend:** Receives auth token from Plex
7. **Frontend:** Sends POST to `/api/auth/plex/login` with `authToken`
8. **Backend:** Validates token with `plex.tv/users/account.json`
9. **Backend:** Gets Plex user data (ID, username, email)
10. **Backend:** Creates/updates user in Supabase `auth.users` table
11. **Backend:** Creates/updates profile in `public.users` table
12. **Backend:** Returns session data to frontend
13. **Frontend:** Stores session, redirects to dashboard

---

## Most Likely Root Cause

Based on the symptoms, the most likely issue is:

**Missing `SUPABASE_SERVICE_KEY` in Railway environment variables**

This would cause:
- ✅ Plex authentication to succeed (doesn't need Supabase)
- ❌ Backend to crash when trying to initialize Supabase client
- ❌ 500 error returned to frontend
- ❌ CORS error (because preflight succeeds but actual request fails)

**Fix:** Add the environment variable in Railway and redeploy.

---

## Need More Help?

If you've gone through all these steps and it's still not working:

1. Copy the **full error from Railway logs**
2. Copy the **full browser console error**
3. Confirm which environment variables are set in Railway
4. Check if tables exist in Supabase
