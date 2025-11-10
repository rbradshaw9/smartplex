# 🚀 Performance & Integration Setup

## ⚠️ CRITICAL FIX NEEDED

### Fix Mixed Content Error in Vercel

Your `NEXT_PUBLIC_API_URL` environment variable in Vercel is currently set to **HTTP** instead of **HTTPS**, which is blocking all API calls.

**To fix:**

1. Go to: https://vercel.com/rbradshaw9s-projects/smartplex/settings/environment-variables

2. Find `NEXT_PUBLIC_API_URL` and change from:
   ```
   ❌ http://smartplexapi-production.up.railway.app
   ```
   To:
   ```
   ✅ https://smartplexapi-production.up.railway.app
   ```
   **Note the `https://` at the start!**

3. Click **"Save"**

4. Go to **Deployments** tab → Click **"..."** on latest deployment → **"Redeploy"**

5. Wait 2-3 minutes for the redeploy to complete

---

## 🚀 Dashboard Performance Improvements

### What Changed

**Before:**
- 🐌 Fetched 50 items from Plex API on every page load (30+ seconds)
- ❌ AI recommendations timeout (502 errors)
- 😤 Had to wait every single time

**After:**
- ⚡ Cached data loads in < 1 second
- 🔄 Background refresh every 5 minutes
- 📦 Full refresh only if cache is > 1 hour old
- 💾 All data stored in Supabase cache tables

### How It Works

1. **First Visit:** Fetches from Plex API, caches in Supabase (~10-20 seconds once)
2. **Second Visit:** Loads from cache instantly (< 1 second)
3. **Background Updates:** Refreshes cache automatically every 5-60 minutes
4. **Always Fresh:** Recent data without waiting

---

## 📊 Database Setup (Run in Supabase SQL Editor)

```sql
-- Copy and paste the entire contents of:
-- packages/db/migrations/003_add_caching_tables.sql

-- This creates:
-- - user_stats_cache (stats like total watched, hours, favorite genre)
-- - watch_history_cache (recent watches with metadata)
-- - recommendations_cache (AI recommendations)
```

### Supabase SQL Editor URL:
https://supabase.com/dashboard/project/lecunkywsfuqumqzddol/sql/new

---

## 🔧 Integration Setup (After Fixing HTTPS)

Once you fix the environment variable and redeploy:

### 1. Test Integrations Page Works
- Visit: https://smartplex-ecru.vercel.app/admin/integrations
- Should load without "Mixed Content" errors

### 2. Add Tautulli
```
Service: Tautulli
Name: My Tautulli
URL: https://goneexploring.myles.usbx.me/tautulli
API Key: 6acb68e71f224bd088fb757379498651
```
Click **"Add Integration"** → Then click **"Test"** button

### 3. Add Sonarr
```
Service: Sonarr
Name: My Sonarr
URL: https://goneexploring.myles.usbx.me/sonarr/
API Key: 6f4be1e9167b46e6b282c5dcc99e3d50
```

### 4. Add Radarr
```
Service: Radarr
Name: My Radarr
URL: https://goneexploring.myles.usbx.me/radarr/
API Key: 00cfaa889c7e4415bb853c0cd15e8aea
```

### 5. Add Overseerr
```
Service: Overseerr
Name: My Overseerr
URL: https://overseerr-goneexploring.myles.usbx.me/
API Key: MTcxNDQxMDE2OTMzMWI4ZTUzZmQ3LWZlOTMtNDQ2YS04MTRjLWFjOGUzOTg4MjJmYQ==
```

---

## ✅ Expected Results

### Dashboard
- ⚡ **Instant load** (< 1 second after first visit)
- 📊 Shows your watch stats immediately
- 🎬 Recent watch history
- 🤖 AI recommendations (when cache builds)

### Integrations
- ✅ All 4 services connect successfully
- 🟢 Status indicators turn green
- 🧪 Test button shows connection details

### Chat
- 💬 AI chat works (was getting 403 before)
- 🎯 Can ask about your library

---

## 🎯 Next Steps

1. **Fix Vercel env var** (CRITICAL - nothing works without this)
2. **Run caching SQL migration** in Supabase
3. **Redeploy Vercel** after env var change
4. **Test dashboard** - should be much faster
5. **Add integrations** - all 4 services
6. **Test cleanup page** - try scanning for candidates

---

## 📝 Notes

- **Cache Age Display:** Dashboard will log "Using cached data (age: X minutes)" in console
- **Background Refresh:** Happens automatically, you won't notice it
- **First Load:** Still takes time to build cache, but only once
- **Chrome Errors:** Ignore `content_script.js` errors - those are browser extension noise

---

## 🐛 Troubleshooting

**If integrations still show "Mixed Content":**
- Check the exact URL in Vercel env vars
- Must start with `https://` not `http://`
- After changing, must redeploy (not just save)

**If dashboard is still slow:**
- Run the SQL migration first
- Clear browser cache (Ctrl+Shift+R)
- Check console for "Using cached data" message

**If AI recommendations fail:**
- This is cached now, so it won't block the page
- May take a minute to generate first time
- Check Railway API logs if persists

---

🚀 **After fixing the HTTPS issue, everything should work smoothly!**
