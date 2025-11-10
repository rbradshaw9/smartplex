# SmartPlex Edge Cases & Considerations

## 🚨 Known Edge Cases & Issues to Address

### 1. Deletion System

#### ✅ ADDRESSED
- **Confirmation Required**: Now requires typing "DELETE" to confirm irreversible deletions
- **Cascade Tracking**: deletion_events table tracks all cascade operations
- **Dry Run First**: UI encourages testing with dry run before real deletion

#### ⚠️ NEEDS CONSIDERATION

**Race Conditions:**
- **Issue**: User deletes item while Plex webhook triggers sync that re-adds it
- **Impact**: File deleted from Plex but immediately re-synced to database
- **Solution**: Add deletion timestamp check in sync logic; skip items deleted within last hour
- **Priority**: Medium

**Concurrent Deletions:**
- **Issue**: Multiple admin users could try deleting same item simultaneously
- **Impact**: Multiple cascade attempts, confusing logs
- **Solution**: Add row-level locking or check deletion_events before starting
- **Priority**: Low (single admin use case)

**Failed Cascade Scenarios:**
- **Issue**: Plex deletion succeeds but Sonarr/Radarr API is down
- **Impact**: File deleted but *arr will re-download it
- **Current**: Status = "partial", logged in deletion_events
- **Enhancement**: Add retry mechanism for failed cascade operations
- **Priority**: Medium

**Storage Calculation:**
- **Issue**: Plex reports file size differently than actual disk usage
- **Impact**: "Space freed" calculation may be inaccurate
- **Current**: Uses Plex's reported size from media parts
- **Enhancement**: Could query filesystem directly (requires server access)
- **Priority**: Low (Plex size is "good enough")

**Orphaned Database Records:**
- **Issue**: Deletion removes from Plex but media_items row stays
- **Impact**: Item appears in future scans as candidate again
- **Solution**: Delete or mark media_items row after successful Plex deletion
- **Priority**: HIGH ⚠️

---

### 2. Sync System

#### ✅ ADDRESSED
- **Real-time Progress**: SSE streams progress with ETA
- **Connection Caching**: PlexConnectionManager reduces connection time
- **Error Handling**: Graceful degradation per-server, per-section

#### ⚠️ NEEDS CONSIDERATION

**SSE Connection Timeout:**
- **Issue**: Large library (10k+ items) sync takes 30+ minutes, browser may timeout
- **Impact**: Sync continues on server but UI loses connection
- **Solution**: Add heartbeat messages every 30s, implement reconnection logic
- **Priority**: Medium

**Memory Usage on Large Libraries:**
- **Issue**: Loading 10k+ items into memory at once
- **Impact**: API server memory spike
- **Current**: Fetches all items, processes one-by-one
- **Enhancement**: Batch processing with pagination
- **Priority**: Low (most libraries < 5k items)

**Duplicate Sync Prevention:**
- **Issue**: User clicks "Sync Library" multiple times rapidly
- **Impact**: Multiple concurrent syncs, database race conditions
- **Solution**: Disable button while syncing (already implemented ✅)
- **Additional**: Add server-side sync lock per user
- **Priority**: Low

**Metadata Conflicts:**
- **Issue**: Plex has item with ID X, Tautulli reports different metadata for same ID
- **Impact**: Upsert overrides with last-write-wins
- **Current**: Plex sync is source of truth
- **Enhancement**: Track metadata source, prefer Plex over Tautulli
- **Priority**: Low

---

### 3. Authentication & Security

#### ✅ ADDRESSED
- **Admin-only deletion**: require_admin dependency on all deletion endpoints
- **Audit logging**: admin_activity_log tracks all actions
- **User isolation**: webhook_secret per user

#### ⚠️ NEEDS CONSIDERATION

**Plex Token in Query String:**
- **Issue**: `?plex_token=xxx` appears in browser history, server logs
- **Impact**: Security risk if logs exposed
- **Current**: Convenient for testing, but not secure
- **Solution**: Move to Authorization header or encrypted cookie
- **Priority**: HIGH ⚠️

**Token Expiration:**
- **Issue**: Plex tokens don't expire by default, but can be revoked
- **Impact**: Sync/deletion fails silently with 401
- **Current**: No token refresh logic
- **Solution**: Catch 401, prompt user to reconnect Plex account
- **Priority**: Medium

**CORS Configuration:**
- **Issue**: API allows all origins in development
- **Current**: `allow_origins=["*"]` in CORS middleware
- **Solution**: Restrict to specific frontend domain in production
- **Priority**: HIGH (before public launch)

**Rate Limiting:**
- **Issue**: No rate limits on sync or deletion endpoints
- **Impact**: User could spam API, exhaust Plex API limits
- **Solution**: Add rate limiting middleware (10 syncs/hour per user)
- **Priority**: Medium

---

### 4. Database & Performance

#### ✅ ADDRESSED
- **Indexes**: Comprehensive indexes on all major tables
- **Partial Indexes**: For filtered queries (WHERE clauses)
- **JSONB**: Flexible storage for varied data

#### ⚠️ NEEDS CONSIDERATION

**Migration Rollback:**
- **Issue**: No down migrations, only up
- **Impact**: Can't easily undo a bad migration
- **Current**: Migrations are additive (safe)
- **Enhancement**: Add rollback SQL for each migration
- **Priority**: Low

**Cascading Deletes:**
- **Issue**: Deleting user cascades to all their data
- **Current**: ON DELETE CASCADE on most foreign keys
- **Risk**: Accidental user deletion wipes everything
- **Solution**: Soft delete users (add deleted_at column)
- **Priority**: Medium

**Full Table Scans:**
- **Issue**: Some queries might not use indexes efficiently
- **Current**: Most queries indexed
- **Check**: Monitor query performance with EXPLAIN ANALYZE
- **Priority**: Low (optimize when needed)

**JSONB Query Performance:**
- **Issue**: Querying nested JSONB fields is slower than columns
- **Current**: Used sparingly (payload, details, metadata)
- **Enhancement**: Add GIN indexes on frequently-queried JSONB fields
- **Priority**: Low

---

### 5. Integration Stability

#### ✅ ADDRESSED
- **Timeout handling**: 10s timeout on API calls
- **Error logging**: All integration errors logged
- **Graceful degradation**: Failed integrations don't block others

#### ⚠️ NEEDS CONSIDERATION

**Sonarr/Radarr API Version Changes:**
- **Issue**: API v3 is current, but v4 may have breaking changes
- **Impact**: Deletion cascade fails silently
- **Current**: Hardcoded to /api/v3/
- **Solution**: Version detection or configuration option
- **Priority**: Low (v3 is stable)

**Overseerr Request Status:**
- **Issue**: Deleting "approved" requests is different than "pending"
- **Current**: Deletes all request statuses
- **Enhancement**: Only delete pending/declined, preserve approved for history
- **Priority**: Low

**Integration Health Checks:**
- **Issue**: No proactive check if Sonarr/Radarr/Overseerr are reachable
- **Impact**: Cascade deletion fails only during deletion attempt
- **Current**: Logged as warning
- **Enhancement**: Add /api/integrations/health endpoint, periodic checks
- **Priority**: Medium

**Webhook Signature Verification:**
- **Issue**: Webhooks not verified (anyone with URL can trigger)
- **Current**: User-specific URL with UUID provides some security
- **Risk**: If URL leaked, malicious webhooks possible
- **Solution**: Add webhook signature verification (HMAC)
- **Priority**: Medium

---

### 6. AI Chat System

#### ✅ ADDRESSED
- **Library context**: Fixed key mismatch
- **Confidence tracking**: AI logs confidence scores
- **Cost tracking**: api_performance_logs table

#### ⚠️ NEEDS CONSIDERATION

**OpenAI Rate Limits:**
- **Issue**: Free tier has strict rate limits
- **Impact**: Chat requests fail during high usage
- **Current**: No rate limit handling
- **Solution**: Implement exponential backoff, queue requests
- **Priority**: Medium

**Context Window Limits:**
- **Issue**: GPT-4o-mini has 128k token limit
- **Impact**: Large library context may exceed limit
- **Current**: Sends full context every time
- **Solution**: Summarize or paginate library data
- **Priority**: Low (most users < 10k items)

**Prompt Injection:**
- **Issue**: User could craft prompts to manipulate system behavior
- **Impact**: AI might leak system prompts or behave unexpectedly
- **Current**: System prompt is fixed
- **Enhancement**: Input sanitization, prompt validation
- **Priority**: Low (single-user system, trusted admin)

---

### 7. Frontend/UX

#### ✅ ADDRESSED
- **Loading states**: Spinners and disabled buttons
- **Error messages**: User-friendly error display
- **Progress tracking**: Real-time sync progress

#### ⚠️ NEEDS CONSIDERATION

**Browser Back Button:**
- **Issue**: User navigates away during deletion, operation continues
- **Impact**: Confusing state, no feedback on completion
- **Solution**: Add warning on page unload if operation in progress
- **Priority**: Low

**Mobile Responsiveness:**
- **Issue**: Deletion table not optimized for mobile
- **Current**: Horizontal scroll works but not ideal
- **Enhancement**: Card layout for mobile, table for desktop
- **Priority**: Low (admin panel typically desktop use)

**Bulk Selection Limits:**
- **Issue**: Selecting 1000+ items could cause UI lag
- **Current**: No limit on selections
- **Solution**: Add pagination or virtual scrolling
- **Priority**: Low (rare use case)

---

## 🎯 Immediate Action Items (Before Next Push)

### HIGH Priority (Must Fix):
1. **Delete media_items row after Plex deletion** ✅ Should implement
   - Add to cascade_deletion_service.py after successful Plex deletion
   - Prevents re-scanning deleted items

2. **Move Plex token to header** ✅ Should implement
   - Change from `?plex_token=` to `Authorization: PlexToken xxx`
   - More secure, won't appear in logs

3. **CORS configuration for production**
   - Add environment-based CORS origins
   - Only allow frontend domain in prod

### MEDIUM Priority (Should Address Soon):
4. **Add heartbeat to SSE sync**
   - Prevents timeout on long syncs
   - Send empty message every 30s

5. **Integration health check endpoint**
   - Proactively verify Sonarr/Radarr/Overseerr connectivity
   - Show status in UI before deletion

6. **Token expiration handling**
   - Catch 401 errors
   - Prompt user to reconnect Plex

### LOW Priority (Nice to Have):
7. **Soft delete for users**
   - Prevents accidental data loss
   - Add deleted_at column

8. **Webhook signature verification**
   - Add HMAC validation
   - Prevents malicious webhook calls

---

## 🧪 Testing Checklist

Before considering production-ready:

- [ ] Test deletion with all cascade scenarios:
  - [ ] Movie in Radarr
  - [ ] TV show in Sonarr
  - [ ] Content with Overseerr request
  - [ ] Content with NO *arr integration (Plex-only)
  
- [ ] Test sync with various library sizes:
  - [ ] Small (< 100 items)
  - [ ] Medium (100-1000 items)
  - [ ] Large (1000-5000 items)
  - [ ] Very large (5000+ items) - may need optimization
  
- [ ] Test error scenarios:
  - [ ] Plex server offline during sync
  - [ ] Sonarr/Radarr API down during deletion
  - [ ] Network timeout during SSE stream
  - [ ] Invalid Plex token
  
- [ ] Test concurrent operations:
  - [ ] Multiple users syncing simultaneously
  - [ ] Sync + deletion at same time
  - [ ] Webhook arrives during manual sync
  
- [ ] Security testing:
  - [ ] Non-admin user attempts deletion
  - [ ] Expired token handling
  - [ ] CORS from unauthorized origin

---

## 📊 Monitoring Recommendations

Once deployed:

1. **Watch deletion_events table**
   - Check for `status='failed'` regularly
   - Investigate partial deletions (cascade failures)

2. **Monitor sync_events**
   - Look for slow syncs (duration_ms > 60000)
   - Check for failed syncs

3. **Track API performance logs**
   - OpenAI costs accumulating
   - Slow endpoints (> 5s response time)

4. **Database size growth**
   - media_items table size
   - Webhook logs accumulation (may need cleanup)

---

## 💡 Future Enhancements

### Short-term (Next Sprint):
- Add deletion scheduling (delete at 3am)
- Bulk deletion rules (delete all movies > 5 years old)
- Restore from backup feature (if files still exist)

### Medium-term (Next Month):
- User-level deletion requests (non-admin users can request deletion)
- Automated cleanup based on storage thresholds
- Email notifications for deletion events

### Long-term (Future):
- Machine learning for predicting unwatched content
- Integration with Tdarr for transcoding before deletion
- Cloud storage migration before deletion (archive to S3)

---

## 🔧 Quick Fixes Needed Now

See immediate action items above - most critical is deleting media_items row and moving token to header.
