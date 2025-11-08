# 🔍 Quick Troubleshooting Steps

Follow these steps IN ORDER to diagnose and fix the authentication issue:

## Step 1: Check Railway Logs (MOST IMPORTANT!)

1. Go to: https://railway.app/
2. Navigate to your project → API service
3. Click "Deployments" → Latest deployment → "View Logs"
4. **Look for error messages** when you try to authenticate

### What to look for:
- ❌ `ValidationError: 1 validation error for Settings` → Missing env vars
- ❌ `KeyError: 'SUPABASE_SERVICE_KEY'` → Missing env var
- ❌ `connection refused` → Supabase URL wrong
- ❌ `401 Unauthorized` → Supabase key invalid
- ✅ Emojis like `🔐 Starting Plex authentication flow...` → Good! Keep reading

**Action:** Copy the error message and check what's missing.

---

## Step 2: Verify Railway Environment Variables

Go to Railway → Project → API Service → Variables tab

Required variables:
- [ ] `SMARTPLEX_ENV` = `production`
- [ ] `SUPABASE_URL` = `https://qqqyzrvwysxuevgsww.supabase.co`
- [ ] `SUPABASE_SERVICE_KEY` = `eyJhbG...` (long JWT token, starts with eyJ)
- [ ] `FRONTEND_URL` = `https://smartplex-ecru.vercel.app`

**To get SUPABASE_SERVICE_KEY:**
1. Supabase dashboard → Your project
2. Settings → API
3. Copy `service_role` key (NOT `anon` key!)
4. Paste into Railway variables

**After adding/changing variables:**
- Railway will automatically redeploy
- Wait 2-3 minutes for deployment to complete

---

## Step 3: Fix Vercel Environment Variable

The frontend is using the wrong API URL!

**Current (WRONG):** `smartplexapi-production.up.railway.app`
**Correct:** `smartplex-production.up.railway.app`

1. Go to: https://vercel.com/
2. Select project → Settings → Environment Variables
3. Find `NEXT_PUBLIC_API_URL`
4. Change to: `https://smartplex-production.up.railway.app`
5. Save
6. Go to Deployments → Latest deployment → Three dots → "Redeploy"
7. ✅ Important: MUST redeploy for env var changes to take effect!

---

## Step 4: Verify Database Schema

Check if tables exist in Supabase:

1. Supabase dashboard → SQL Editor
2. Run this query:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   ORDER BY table_name;
   ```
3. Should see these tables:
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
3. Wait 30 seconds

---

## Step 5: Test with New Logging

Now that we've added detailed logging:

1. Try to authenticate with Plex again
2. Check Railway logs (Step 1)
3. You should see emoji logs like:
   ```
   🔐 Starting Plex authentication flow...
   📡 Validating Plex token with plex.tv...
   ✅ Plex user validated: username (ID: 12345)
   📧 Using email: user@example.com
   🔍 Checking for existing Supabase auth user...
   ```
4. **Find where it stops** - that's your problem!

---

## Step 6: Test Locally (Optional)

If you want to test locally:

```bash
cd apps/api

# Set environment variables
export SUPABASE_URL="https://qqqyzrvwysxuevgsww.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"
export FRONTEND_URL="https://smartplex-ecru.vercel.app"
export SMARTPLEX_ENV="development"

# Run diagnostics
python test_diagnostics.py

# Or test with a real Plex token
python test_diagnostics.py "your-plex-token-here"
```

---

## Common Issues & Solutions

### Issue: `ValidationError for Settings`
**Cause:** Missing environment variables in Railway
**Fix:** Add all 4 required env vars (Step 2)

### Issue: CORS error in browser
**Cause:** Wrong `FRONTEND_URL` or wrong `NEXT_PUBLIC_API_URL`
**Fix:** Fix both (Steps 2 & 3), redeploy both services

### Issue: 404 Not Found
**Cause:** Wrong API URL in frontend
**Fix:** Fix `NEXT_PUBLIC_API_URL` in Vercel (Step 3)

### Issue: Database errors
**Cause:** Schema not deployed
**Fix:** Run schema.sql and rls.sql (Step 4)

### Issue: `Invalid Plex token`
**Cause:** Token expired (normal!)
**Fix:** Just try logging in again - Plex generates new token

---

## Quick Test Commands

Test API health:
```bash
curl https://smartplex-production.up.railway.app/health
```

Test CORS:
```bash
curl -X OPTIONS https://smartplex-production.up.railway.app/api/auth/plex/login \
  -H "Origin: https://smartplex-ecru.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

---

## What Success Looks Like

Railway logs should show:
```
🚀 SmartPlex API starting up...
🔧 Environment: production
🔗 Supabase URL: https://qqqyzrvwysxuevgsww.supabase.co
🔑 Supabase Service Key: SET
🌐 Frontend URL: https://smartplex-ecru.vercel.app
🔒 CORS allowed origins: ['http://localhost:3000', 'https://smartplex-ecru.vercel.app', 'https://*.vercel.app']
```

When you authenticate:
```
🔐 Starting Plex authentication flow...
📡 Validating Plex token with plex.tv...
✅ Plex user validated: username (ID: 12345)
📧 Using email: user@email.com
✅ Found existing auth user: uuid-here
✅ Updated auth user metadata
✅ Found existing profile, updating...
✅ Profile updated
🎫 Generating session token...
✅ Authentication successful!
```

Frontend should:
1. Show Plex window
2. User authenticates
3. Window closes automatically
4. Redirect to dashboard
5. ✅ Success!
