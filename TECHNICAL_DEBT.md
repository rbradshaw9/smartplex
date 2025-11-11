# 📝 SmartPlex Technical Debt & TODOs

## 🔴 Critical (Security & Data Integrity)

### 1. **Plex Token Storage** (Multiple Files)
**Issue**: Plex tokens not stored in database, only in frontend localStorage

**Affected Files**:
- `apps/api/app/api/routes/plex.py:71`
- `apps/api/app/api/routes/webhooks.py:106`
- `apps/api/app/services/cascade_deletion_service.py:235`
- `apps/api/app/services/plex_collections.py:60, 248`
- `apps/api/app/services/analytics_service.py:149`

**Current State**:
- Frontend stores Plex token in localStorage
- Backend endpoints require `plex_token` as query parameter
- Webhooks and background jobs can't access token

**Solution Options**:
1. **Add `plex_token` column to `users` table** (encrypted)
2. **Store in `integrations` table** as "plex" service type
3. **Use Plex OAuth refresh tokens** for long-term access

**Impact**: HIGH
- Webhooks can't create Plex collections
- Background sync requires manual token
- Security: tokens passed in URLs (logged)

**Recommendation**: Add encrypted `plex_token` to `users` table
```sql
ALTER TABLE users ADD COLUMN plex_token_encrypted TEXT;
```

---

### 2. **API Key Encryption**
**Issue**: Integration API keys stored in plain text

**Affected Files**:
- `apps/api/app/api/routes/integrations.py:161`

**Current State**:
```python
'api_key': integration.api_key,  # TODO: Encrypt this
```

**Solution**:
- Use `pgcrypto` extension (already enabled)
- Encrypt with `pgp_sym_encrypt()`
- Decrypt only when needed

**Impact**: MEDIUM
- Security risk if database compromised
- Tautulli, Overseerr, Sonarr, Radarr keys exposed

**Recommendation**:
```sql
-- Migration to encrypt existing keys
UPDATE integrations 
SET api_key_encrypted = pgp_sym_encrypt(api_key, 'encryption_key')
WHERE api_key IS NOT NULL;

ALTER TABLE integrations DROP COLUMN api_key;
```

---

## 🟡 High Priority (Functionality)

### 3. **Actual Deletion Implementation**
**Issue**: Deletions only mark as deleted, don't actually remove files

**Affected Files**:
- `apps/api/app/services/deletion_service.py:236, 314, 319, 324`

**Current State**:
```python
# TODO: Implement actual deletion via Plex/Sonarr/Radarr APIs
# Currently just marks as deleted in database
```

**Required Implementations**:
1. **Plex Deletion**: Use `item.delete()` via PlexAPI
2. **Sonarr Deletion**: `DELETE /api/v3/series/{id}?deleteFiles=true`
3. **Radarr Deletion**: `DELETE /api/v3/movie/{id}?deleteFiles=true`

**Impact**: HIGH
- Users expect files to be removed
- Storage not actually freed
- Manual cleanup required

**Recommendation**: Implement in phases
1. Phase 1: Plex deletion (safest)
2. Phase 2: Sonarr/Radarr deletion (with confirmation)
3. Phase 3: Filesystem deletion (most dangerous)

---

### 4. **Overseerr Request Status Webhooks**
**Issue**: Request status not updated in database after approval/rejection

**Affected Files**:
- `apps/api/app/api/routes/webhooks.py:730`

**Current State**:
```python
# TODO: Update request status in database
```

**Solution**:
- Create `media_requests` table
- Track request status (pending, approved, rejected)
- Update via webhook

**Impact**: MEDIUM
- Can't show request history
- No request analytics
- Users don't know request status

---

## 🟢 Medium Priority (Features)

### 5. **Background Scheduler Tasks**
**Issue**: Placeholder implementations for automated tasks

**Affected Files**:
- `apps/core/scheduler.py:177` - Full Plex library sync
- `apps/core/scheduler.py:211` - Integration health checks

**Current State**:
```python
# TODO: Implement full Plex library sync
# TODO: Add health check methods to each integration service
```

**Recommended Implementation**:
1. **Auto Plex Sync**: Nightly full sync
2. **Health Checks**: Ping integrations every 5 minutes
3. **Storage Monitoring**: Update capacity daily
4. **Analytics Sync**: Sync view counts hourly

---

### 6. **Integration Health Checking**
**Issue**: No way to verify integrations are working

**Impact**: MEDIUM
- Broken integrations go unnoticed
- Users see stale data
- Webhooks fail silently

**Solution**:
```python
class IntegrationHealthCheck:
    async def check_tautulli(integration):
        try:
            response = await call_api(f"{integration.url}/api/v2?cmd=get_activity")
            return response.status_code == 200
        except:
            return False
```

---

## 🔵 Low Priority (Nice to Have)

### 7. **Debug Endpoints - Tautulli Integration Check**
**Issue**: Debug endpoint doesn't verify Tautulli integration exists

**Affected Files**:
- `apps/api/app/api/routes/debug.py:178`

**Current State**:
```python
"tautulli_integration_exists": None,  # TODO: check integrations table
```

**Fix**: Query integrations table
```python
tautulli = await supabase.table('integrations')\
    .select('*')\
    .eq('service', 'tautulli')\
    .eq('user_id', user_id)\
    .execute()
tautulli_exists = len(tautulli.data) > 0
```

---

## ✅ Recently Completed

### ✓ Storage Count Fix (1000 limit)
**Status**: FIXED (commit fd30c48)
- Added `.limit(100000)` to storage query
- Resolved count mismatch

### ✓ Sentry Error Fixes
**Status**: FIXED (commit 6f2c613, b9cd689)
- Fixed `users.plex_token` AttributeError
- Fixed KeyError 'skipped' in deletions
- Added null checks

### ✓ Media Quality Tracking
**Status**: IMPLEMENTED (commit 29e6e7d)
- Added resolution, codec, container tracking
- Created quality analysis views
- New API endpoints

---

## 📊 Priority Matrix

### Must Have (Beta Blocker):
1. ✅ Storage count fix
2. ✅ Sentry error fixes
3. ✅ Media quality tracking
4. 🟡 Plex token storage (for webhooks/background jobs)

### Should Have (Beta Nice-to-Have):
5. 🟡 Actual deletion implementation
6. 🟢 Integration health checks
7. 🟢 API key encryption

### Could Have (Post-Beta):
8. 🔵 Request status tracking
9. 🔵 Automated scheduler tasks
10. 🔵 Debug endpoint improvements

---

## 🎯 Recommended Implementation Order

### Sprint 1 (This Week):
1. **Test quality tracking** - Verify after sync
2. **Add Plex token to users table** - Enable webhooks
3. **Implement Plex deletion** - Actual file removal

### Sprint 2 (Next Week):
4. **Integration health checks** - Auto-detect failures
5. **Encrypt API keys** - Security hardening
6. **Request status tracking** - Better UX

### Sprint 3 (Future):
7. **Sonarr/Radarr deletion** - Full automation
8. **Background scheduler** - Auto-sync
9. **Advanced analytics** - More insights

---

## 🛠️ Quick Wins (< 1 Hour Each)

### 1. Fix Debug Endpoint
**File**: `apps/api/app/api/routes/debug.py:178`
**Effort**: 10 minutes
```python
tautulli_result = supabase.table('integrations')\
    .select('*')\
    .eq('service', 'tautulli')\
    .eq('user_id', user_id)\
    .execute()
info["tautulli_integration_exists"] = len(tautulli_result.data or []) > 0
```

### 2. Add Storage Capacity Validation
**File**: `apps/api/app/api/routes/system_config.py`
**Effort**: 15 minutes
```python
# Validate capacity > current usage
current_usage = await get_current_storage_stats(supabase)
if config.total_gb < current_usage["total_used_gb"]:
    raise HTTPException(400, "Capacity cannot be less than current usage")
```

### 3. Add Quality Metadata to Storage Info Endpoint
**File**: `apps/api/app/api/routes/plex_sync.py`
**Effort**: 20 minutes
```python
# Add quality breakdown to storage-info response
quality_summary = supabase.table('storage_quality_analysis').select('*').execute()
storage_info["quality_breakdown"] = quality_summary.data
```

---

## 📝 Notes

### Plex Token Security Considerations:
- **Option 1**: Encrypt in database (pgcrypto)
  - Pros: Secure, accessible to backend
  - Cons: Need to manage encryption key
  
- **Option 2**: Store refresh token, get access token as needed
  - Pros: Most secure, limited scope
  - Cons: Complex OAuth flow
  
- **Option 3**: User provides token per-operation
  - Pros: No storage needed
  - Cons: Poor UX, breaks webhooks

**Recommendation**: Option 1 with encrypted column

### Deletion Safety:
- Always require explicit confirmation
- Log all deletions to audit trail
- Support "dry run" mode
- Allow undo within 24 hours (quarantine)
- Send email notifications for large deletions

### Integration Health:
- Check every 5 minutes
- Set `status='error'` on failure
- Send admin notification after 3 failures
- Auto-disable after 10 failures
- Log failure reasons

---

**Last Updated**: November 11, 2025
**Total TODOs**: 10 tracked
**Completion Rate**: 30% (3/10 critical items done)
