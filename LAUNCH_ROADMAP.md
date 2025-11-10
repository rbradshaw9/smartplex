# 🚀 SmartPlex Launch Roadmap

## Current Status: 70% Complete
**Estimated time to MVP launch: 12-16 hours**

---

## 🔥 Phase 0: Critical Blockers (4-5 hours)
**Cannot launch without these - they break core functionality**

### 1. Fix Webhook Tenant Isolation ⚠️ CRITICAL - SECURITY/DATA CORRUPTION
**Problem**: Webhooks are global - can't tell which user's Plex server sent them. Multi-user = data corruption.

**Solution**: User-specific webhook URLs + match by Plex machine_id
- Add `user_id` to webhook endpoints: `/api/webhooks/plex/{user_id}`
- Extract `Server.uuid` from Plex webhook payload
- Look up user by `servers.machine_id`
- Add webhook authentication tokens

**Files to modify**:
- `apps/api/app/api/routes/webhooks.py`
- `packages/db/migrations/006_add_webhook_user_isolation.sql`

**Impact**: Prevents data corruption, enables multi-user webhooks

---

### 2. Fix Plex Connection Caching ⚠️ CRITICAL - PERFORMANCE
**Problem**: Every sync tries 4 different Plex URLs, taking 30+ seconds with timeouts.

**Solution**: Cache the working connection URL per server
- Add `preferred_connection_url` to `servers` table
- Test URLs once, cache winner
- Reduce timeout from 10s to 5s
- Add connection pooling

**Files to modify**:
- `apps/api/app/core/plex.py`
- `apps/api/app/api/routes/plex.py`
- `packages/db/migrations/006_add_connection_caching.sql`

**Impact**: 30+ seconds → 2-3 seconds for syncs

---

### 3. Fix Database NULL Values ⚠️ CRITICAL - RECOMMENDATIONS BROKEN
**Problem**: `'>=' not supported between instances of 'NoneType' and 'int'`

**Solution**: Find and fix NULL values, add proper defaults
- Query for NULL values in `media_items` scoring columns
- Set default values (0 for numbers, empty string for text)
- Add NOT NULL constraints
- Add null checks in scoring logic

**Files to modify**:
- `apps/api/app/api/routes/ai.py`
- `packages/db/migrations/006_fix_null_values.sql`

**Impact**: Recommendations work for all users

---

### 4. Fix AI Chat Library Context ⚠️ CRITICAL - CHAT BROKEN
**Problem**: AI says "I don't have direct access to your movie library" but should see it.

**Solution**: Pass user's library data to OpenAI context
- Fetch user's `media_items` + `user_stats`
- Format as context for OpenAI
- Include: titles, genres, watch counts, ratings
- Add library summary to system prompt

**Files to modify**:
- `apps/api/app/api/routes/ai.py`

**Impact**: Chat becomes useful instead of useless

---

### 5. Move Plex Token to Header ⚠️ SECURITY
**Problem**: Plex token in query string (visible in logs, browser history).

**Solution**: Use `X-Plex-Token` header
- Update frontend to send token in header
- Update backend to read from header
- Remove token from query params

**Files to modify**:
- `apps/web/src/components/dashboard/dashboard.tsx`
- `apps/api/app/api/routes/plex.py`

**Impact**: Basic security hygiene

---

### 6. Add Server Foreign Key Constraint ⚠️ DATA INTEGRITY
**Problem**: `integrations.server_id` is TEXT, not proper foreign key.

**Solution**: Add foreign key constraint
```sql
ALTER TABLE integrations 
  ADD CONSTRAINT fk_integrations_server 
  FOREIGN KEY (server_id) REFERENCES servers(id);
```

**Files to modify**:
- `packages/db/migrations/006_add_foreign_keys.sql`

**Impact**: Prevent orphaned records, data integrity

---

## 🎯 Phase 1: Complete Core Features (5-6 hours)
**Need these for MVP to be functional**

### 7. Complete Plex Library Sync (Webhook TODO)
**Problem**: Line 67-83 in `webhooks.py` is empty - Plex webhooks do nothing.

**Solution**: Implement `trigger_plex_library_sync_background()`
- Connect to Plex server
- Fetch library section items
- Extract metadata and IDs
- Upsert to `media_items` table
- Match with existing records

**Files to modify**:
- `apps/api/app/api/routes/webhooks.py`
- `apps/api/app/services/plex_library_sync.py` (new)

**Impact**: Webhooks actually work

---

### 8. Add Request Button + Modal
**Problem**: No request button exists anywhere - core feature missing.

**Solution**: Build request UI
- Add "Request Content" button to dashboard
- Create request modal with Overseerr search
- Display TMDB results with posters
- Submit request to Overseerr API
- Show success/error feedback

**Files to modify**:
- `apps/web/src/components/dashboard/dashboard.tsx`
- `apps/web/src/components/request-modal.tsx` (new)
- `apps/api/app/api/routes/integrations.py`

**Impact**: Users can actually request content

---

### 9. Add Background Job Scheduler
**Problem**: `sync_schedule` table exists but nothing checks it - scheduled syncs don't run.

**Solution**: Implement APScheduler
- Add APScheduler to FastAPI lifespan
- Check `sync_schedule` table every minute
- Trigger syncs when `next_run_at` is past
- Update `last_run_at` and `run_count`
- Handle errors gracefully

**Files to modify**:
- `apps/api/app/main.py`
- `apps/api/app/core/scheduler.py` (already exists, needs implementation)
- `requirements.txt` (add `apscheduler`)

**Impact**: Fallback syncs work when webhooks fail

---

### 10. Add Integration Health Checks
**Problem**: No way to test if integrations work after setup.

**Solution**: Add test endpoint
- `POST /api/integrations/{id}/test` - Test connection
- Try to connect and fetch basic data
- Return success/error with details
- Show health status in UI (green/yellow/red)

**Files to modify**:
- `apps/api/app/api/routes/integrations.py`
- `apps/web/src/app/admin/integrations/page.tsx`

**Impact**: Users know if setup worked

---

### 11. Add Proper Error Handling & Retries
**Problem**: Silent failures - users see "Connecting..." forever.

**Solution**: Add retry logic and error messages
- Retry failed API calls 3x with exponential backoff
- Show error messages to user
- Fall back to cached data when APIs fail
- Add circuit breaker for repeated failures

**Files to modify**:
- `apps/api/app/core/plex.py`
- `apps/api/app/services/integrations/base.py`
- `apps/web/src/components/dashboard/dashboard.tsx`

**Impact**: Better UX, no silent failures

---

### 12. Add Webhook Signature Verification
**Problem**: Anyone can POST fake webhooks - security risk.

**Solution**: Verify webhook authenticity
- Generate unique webhook secret per user
- Store in `users` table or environment
- Verify signature on incoming webhooks
- Reject unsigned/invalid webhooks
- Add rate limiting per source

**Files to modify**:
- `apps/api/app/api/routes/webhooks.py`
- `packages/db/migrations/007_add_webhook_secrets.sql`

**Impact**: Security against fake webhooks

---

## 📊 Phase 2: Data & Performance (3-4 hours)
**Should fix soon after launch**

### 13. Add Missing Database Indexes
**Problem**: Queries will be slow with large datasets.

**Solution**: Add performance indexes
```sql
CREATE INDEX idx_media_items_tmdb_id ON media_items(tmdb_id);
CREATE INDEX idx_media_items_tvdb_id ON media_items(tvdb_id);
CREATE INDEX idx_media_items_type ON media_items(type);
CREATE INDEX idx_media_items_added_at ON media_items(added_at DESC);
CREATE INDEX idx_user_stats_user_last_played ON user_stats(user_id, last_played_at DESC);
```

**Files to modify**:
- `packages/db/migrations/008_add_performance_indexes.sql`

**Impact**: Faster queries at scale

---

### 14. Implement Incremental Sync
**Problem**: Every sync fetches full 25+ items, taking 30+ seconds.

**Solution**: Only sync new items
- Store `last_sync_at` timestamp
- Fetch only items newer than last sync
- Use Plex's `updatedAt` filter
- Fall back to full sync if > 7 days

**Files to modify**:
- `apps/api/app/api/routes/plex.py`
- `apps/api/app/core/cache.py`

**Impact**: 30s → 2s for subsequent syncs

---

### 15. Add Deletion Audit Log
**Problem**: No record of what was deleted or why.

**Solution**: Create deletion log table
```sql
CREATE TABLE deletion_log (
  id UUID PRIMARY KEY,
  media_item_id UUID REFERENCES media_items(id),
  title TEXT NOT NULL,
  deleted_at TIMESTAMP DEFAULT NOW(),
  deleted_by UUID REFERENCES users(id),
  reason TEXT,
  score DECIMAL,
  can_undo BOOLEAN DEFAULT FALSE
);
```

**Files to modify**:
- `packages/db/migrations/008_add_deletion_log.sql`
- `apps/api/app/services/deletion_service.py`

**Impact**: Audit trail, possible undo

---

### 16. Add Content Requests Tracking
**Problem**: Users can't see what they requested or status.

**Solution**: Create requests table
```sql
CREATE TABLE content_requests (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  media_type TEXT, -- 'movie' or 'tv'
  tmdb_id INTEGER,
  title TEXT,
  status TEXT, -- 'pending', 'approved', 'available', 'declined'
  requested_at TIMESTAMP DEFAULT NOW(),
  available_at TIMESTAMP,
  overseerr_request_id INTEGER
);
```

**Files to modify**:
- `packages/db/migrations/009_add_content_requests.sql`
- `apps/api/app/api/routes/integrations.py`
- `apps/web/src/app/requests/page.tsx` (new)

**Impact**: Users can track request status

---

### 17. Optimize Cache Strategy
**Problem**: Cache invalidation is basic, causes stale data.

**Solution**: Smarter cache management
- Cache per endpoint/resource
- Use Redis for distributed cache (optional)
- Add cache warming on webhook
- Implement cache tags for granular invalidation

**Files to modify**:
- `apps/api/app/core/cache.py`

**Impact**: Fresher data, less API load

---

## 👥 Phase 3: User Experience (2-3 hours)
**Polish for better UX**

### 18. Build Onboarding Flow
**Problem**: New users see empty dashboard, don't know what to do.

**Solution**: First-time user wizard
- Detect first login (no Plex server connected)
- Show modal: "Welcome! Let's connect your Plex server"
- Step 1: Connect Plex
- Step 2: Initial sync
- Step 3: Done! Here's your dashboard

**Files to modify**:
- `apps/web/src/components/onboarding/onboarding-wizard.tsx` (new)
- `apps/web/src/app/dashboard/page.tsx`

**Impact**: Better first impression

---

### 19. Add Empty States
**Problem**: Empty sections show nothing - confusing UX.

**Solution**: Empty state messaging
- No watch history: "Connect your Plex server to see history"
- No recommendations: "Watch some content first!"
- No requests: "Request your first movie or show"

**Files to modify**:
- `apps/web/src/components/dashboard/*.tsx`

**Impact**: Clearer UX

---

### 20. Create "My Requests" Page
**Problem**: No way to see request history/status.

**Solution**: Requests page
- List all user's requests
- Show status badges (pending/approved/available)
- Filter by status
- Show estimated availability time

**Files to modify**:
- `apps/web/src/app/requests/page.tsx` (new)
- `apps/api/app/api/routes/integrations.py`

**Impact**: Users track their requests

---

### 21. Add Request Notifications
**Problem**: Users don't know when requests are ready.

**Solution**: Notification system
- Webhook from Overseerr when available
- Store notification in DB
- Show badge/alert in UI
- Optional: Email notification

**Files to modify**:
- `apps/api/app/api/routes/webhooks.py` (Overseerr handler)
- `packages/db/migrations/010_add_notifications.sql`
- `apps/web/src/components/notifications.tsx` (new)

**Impact**: Users discover new content faster

---

## 🔧 Phase 4: Operations & Polish (2-3 hours)
**Can wait until after launch**

### 22. Enhance Health Check Endpoint
**Problem**: `/health` doesn't actually check if system is healthy.

**Solution**: Comprehensive health check
```python
GET /health
{
  "status": "healthy",
  "database": "connected",
  "plex": "reachable",
  "redis": "connected",
  "integrations": {
    "tautulli": "healthy",
    "overseerr": "healthy"
  },
  "last_sync": "2 minutes ago"
}
```

**Files to modify**:
- `apps/api/app/api/routes/health.py`

**Impact**: Better monitoring

---

### 23. Add Structured Logging
**Problem**: Hard to debug production issues.

**Solution**: Structured JSON logging
- Use structlog or loguru
- Include request_id, user_id in all logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Send errors to Sentry (optional)

**Files to modify**:
- `apps/api/app/core/logging.py`
- `requirements.txt`

**Impact**: Easier debugging

---

### 24. Add Rate Limiting
**Problem**: No protection against abuse/spam.

**Solution**: Rate limiting middleware
- Limit chat: 20 requests/minute per user
- Limit sync: 10 requests/hour per user
- Limit webhooks: 100 requests/minute per IP
- Return 429 Too Many Requests

**Files to modify**:
- `apps/api/app/middleware/rate_limit.py` (new)
- `apps/api/app/main.py`

**Impact**: Prevent abuse, control costs

---

### 25. Add API Documentation
**Problem**: No docs for API endpoints.

**Solution**: OpenAPI/Swagger docs
- Enable FastAPI docs in production
- Document all endpoints
- Add examples
- Document webhook payload formats

**Files to modify**:
- `apps/api/app/main.py` (enable docs)
- Add docstrings to all endpoints

**Impact**: Easier integration, debugging

---

### 26. Build Admin Dashboard
**Problem**: No visibility into system health.

**Solution**: Admin monitoring page
- Show recent syncs
- Show webhook activity
- Show error rates
- Show user count, content count
- System metrics (CPU, memory, DB size)

**Files to modify**:
- `apps/web/src/app/admin/dashboard/page.tsx` (new)
- `apps/api/app/api/routes/admin/monitoring.py` (new)

**Impact**: Better operations visibility

---

## 🎯 Absolute Minimum for MVP Launch

**Must complete (7 items, ~8-10 hours)**:
1. ✅ Fix webhook tenant isolation
2. ✅ Fix Plex connection caching
3. ✅ Fix database NULL values
4. ✅ Fix AI chat library context
5. ✅ Complete Plex webhook sync
6. ✅ Add request button + modal
7. ✅ Add background job scheduler

**Everything else** can be post-launch improvements.

---

## 📅 Suggested Timeline

### **Week 1: Critical Blockers**
- Days 1-2: Phase 0 (items 1-6)
- Days 3-4: Phase 1 (items 7-12)
- Day 5: Testing & bug fixes

### **Week 2: Launch & Iterate**
- Day 1: Launch MVP
- Days 2-5: Phase 2 (items 13-17) based on user feedback

### **Week 3: Polish**
- Days 1-3: Phase 3 (items 18-21)
- Days 4-5: Phase 4 (items 22-26)

---

## 🚀 Launch Checklist

Before going live, ensure:
- [ ] All Phase 0 items complete
- [ ] All Phase 1 items complete (or acceptable workarounds)
- [ ] Database migrations run on production
- [ ] Environment variables set on Railway/Vercel
- [ ] Webhooks configured and tested
- [ ] Error tracking enabled (Sentry)
- [ ] Monitoring/alerting set up
- [ ] Backup strategy in place
- [ ] Rate limiting active
- [ ] Security review complete
- [ ] Load testing done (optional but recommended)

---

## 📝 Notes

- **Estimated total time to MVP**: 12-16 hours of focused work
- **Current completion**: ~70%
- **Biggest blockers**: Webhook isolation, Plex caching, NULL values, AI context
- **Nice to have but not critical**: Most of Phase 3 and all of Phase 4

---

Last updated: 2025-11-10
