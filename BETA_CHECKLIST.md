# SmartPlex Beta Deployment Checklist

## ✅ Completed Backend Features

### Bug Fixes
- [x] Storage count shows correct total (fixed Supabase 1000 limit)
- [x] Fixed users.plex_token query errors (column doesn't exist)
- [x] Fixed KeyError 'skipped' in cascade deletion
- [x] All deletion service methods return consistent 'skipped' key

### New Features
- [x] **Analytics Service** - Hybrid Tautulli/Plex API data source
  - Auto-fallback to Plex aggregate data when Tautulli unavailable
  - `GET /api/analytics/data-source` - check what's available
  - `POST /api/analytics/sync/plex-aggregate` - sync from Plex API
  - `GET /api/analytics/status` - status for all servers

- [x] **Watch List API** - Save AI recommendations for later
  - `POST /api/watch-list` - add item
  - `GET /api/watch-list` - list with filters  
  - `GET /api/watch-list/{id}` - get single item
  - `PATCH /api/watch-list/{id}` - update priority/notes
  - `DELETE /api/watch-list/{id}` - remove item
  - `DELETE /api/watch-list?confirm=true` - clear all

## 🚧 Pending Tasks

### Database Migration
- [ ] **Run migration 016_add_watch_list.sql** on Supabase production
  - Creates `watch_list` table
  - Creates `watch_list_with_details` view
  - Adds indexes for performance

### Frontend Features
- [ ] **Watch List UI Components**
  - Add "Save to Watch List" buttons on AI recommendations
  - Create `/watch-list` page showing saved items
  - Priority selector (0-10 stars/slider)
  - Unwatched badge
  - Quick remove button

- [ ] **Global Activity Monitor**
  - Header component showing active jobs
  - Real-time job status (Plex sync, Tautulli sync, deletions)
  - Click to expand details modal
  - Progress bars for each job
  - Cancel buttons

- [ ] **Analytics Data Source Indicator**
  - Show badge on dashboard: "Using Tautulli" or "Using Plex API (aggregate only)"
  - Recommendation to install Tautulli when using fallback
  - Button to sync Plex aggregate data

### Optional Integrations
- [ ] **Ultra.cc Storage API** (awaiting docs)
  - Auto-fetch storage capacity
  - Replace manual configuration
  - Real-time usage updates

## 📋 Testing Checklist

### Backend APIs
- [ ] Test watch list CRUD operations
- [ ] Test analytics data source detection
- [ ] Test Plex aggregate sync with token
- [ ] Verify storage count shows correct number
- [ ] Check Sentry for no new errors

### Frontend
- [ ] Watch list page loads
- [ ] Can add items from recommendations
- [ ] Can update priority and notes
- [ ] Can remove items
- [ ] Activity monitor shows active jobs
- [ ] Analytics badge shows correct source

### Integration Testing
- [ ] Test with Tautulli enabled (should use Tautulli)
- [ ] Test without Tautulli (should fallback to Plex API)
- [ ] Test deletion with cascade to Sonarr/Radarr/Overseerr
- [ ] Verify no 204 errors in Sentry

## 🚀 Deployment Steps

1. **Database Migration**
   ```sql
   -- Run in Supabase SQL Editor
   -- File: packages/db/migrations/016_add_watch_list.sql
   ```

2. **Push Backend**
   ```bash
   git push origin main  # Triggers Railway deployment
   ```

3. **Deploy Frontend**
   - Vercel auto-deploys from main branch
   - Verify deployment completes successfully

4. **Verify Health**
   - Check Railway logs for startup errors
   - Hit `/health` endpoint
   - Check Sentry for any new errors

## 📊 Success Metrics

- [ ] Storage shows >1000 items correctly
- [ ] No Sentry errors for 24 hours
- [ ] Watch list operations work smoothly
- [ ] Analytics fallback works without Tautulli
- [ ] Activity monitor shows all background jobs
- [ ] Deletion cascade works for all services

## 🔧 Known Limitations

1. **Plex Token Storage** - Not stored in database yet
   - Tokens passed from frontend as query params
   - Server-side operations (webhooks, collections) temporarily disabled
   - TODO: Add secure token storage for admin operations

2. **Ultra.cc Integration** - Pending API documentation
   - Manual storage capacity configuration still required
   - Will be replaced once API details provided

3. **Activity Monitor** - UI not yet implemented
   - Backend jobs run but no global visibility
   - Coming in next update

## 📝 Notes for Beta Users

### What's Working Great
- ✅ Tautulli sync with progress bar
- ✅ AI recommendations (chat + recommendations page)
- ✅ Deletion rules and candidates
- ✅ Storage tracking (now accurate!)
- ✅ Watch list backend (ready for UI)

### Known Issues
- ⚠️ Plex collection feature temporarily disabled (token issue)
- ⚠️ Webhook sync disabled (token issue)
- ⚠️ Activity monitor UI pending

### Getting Help
- Check Railway logs: `railway logs`
- Check Sentry for errors
- GitHub Issues: https://github.com/rbradshaw9/smartplex/issues
