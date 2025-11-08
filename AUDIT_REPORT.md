# 🔍 SmartPlex Codebase Audit Report

## Executive Summary

This comprehensive audit identified **23 critical and high-severity issues** across the SmartPlex codebase that could cause production failures, security vulnerabilities, and poor user experience.

**Audit Date:** November 8, 2025  
**Scope:** Backend API, Frontend components, Database schema, Configuration
**Status:** 🔴 **CRITICAL ISSUES FOUND**

---

## Critical Issues (Production-Breaking) 🔴

### 1. ❌ **Unhashable Settings Object (FIXED)**
**Location:** `apps/api/app/config.py`  
**Severity:** CRITICAL  
**Status:** ✅ FIXED

**Issue:**
- Used `@lru_cache()` decorator on `get_settings()` with Pydantic `BaseSettings`
- Pydantic objects aren't hashable by default
- Caused `TypeError: unhashable type: 'Settings'` in production

**Impact:** Complete API failure - 500 errors on all endpoints using Settings dependency

**Fix Applied:**
- Removed `@lru_cache()` decorator
- Implemented singleton pattern instead

---

### 2. ❌ **Same Issue in supabase.py - NOT FIXED**
**Location:** `apps/api/app/core/supabase.py:21`  
**Severity:** CRITICAL  
**Status:** 🔴 **STILL EXISTS**

```python
@lru_cache()
def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
```

**Issue:**
- **SAME BUG** - `@lru_cache()` with unhashable Settings object
- Will cause the exact same 500 error
- Only reason it hasn't crashed yet: Settings parameter prevents caching

**Impact:** Potential production failure when FastAPI tries to cache this dependency

**Fix Required:**
```python
# Remove @lru_cache() decorator
_supabase_client: Optional[Client] = None

def get_supabase_client(settings: Settings = Depends(get_settings)) -> Client:
    """Get cached Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_key,
            )
        except Exception as e:
            raise DatabaseException(
                message="Failed to initialize Supabase client",
                details=str(e)
            )
    return _supabase_client
```

---

### 3. ❌ **No Error Handling for Supabase Operations**
**Location:** Multiple files - `plex_auth.py`, `health.py`  
**Severity:** CRITICAL  
**Status:** 🔴 **NEEDS FIX**

**Issue:**
- Database operations like `.execute()` can fail silently
- No checking of response status or data
- Supabase errors aren't caught properly

**Examples:**
```python
# plex_auth.py:106 - No error handling
existing_profile = supabase.table('users').select('*').eq('id', user_id).execute()

if existing_profile.data:  # What if .data is None? What if query failed?
    # Process data
```

**Impact:** 
- Silent failures when database is down
- Crashes with AttributeError if response structure changes
- Data corruption if partial writes succeed

**Fix Required:**
```python
try:
    response = supabase.table('users').select('*').eq('id', user_id).execute()
    
    if response.status_code >= 400:
        raise DatabaseException(f"Query failed: {response.status_code}")
    
    if not response.data:
        # Handle empty result
        pass
except Exception as e:
    print(f"❌ Database error: {e}")
    raise DatabaseException("Failed to query users table", details=str(e))
```

---

### 4. ❌ **Race Condition in Plex Auth**
**Location:** `apps/api/app/api/routes/plex_auth.py:60-130`  
**Severity:** HIGH  
**Status:** 🔴 **NEEDS FIX**

**Issue:**
- Checks if user exists, then creates/updates
- No transaction wrapping or locking
- Two simultaneous logins could create duplicate users

**Example:**
```python
existing_auth_user = next((u for u in auth_user_response if u.email == email), None)

if existing_auth_user:
    # UPDATE
else:
    # CREATE - but what if another request just created it?
```

**Impact:**
- Duplicate user records in database
- Primary key violations
- Inconsistent user state

**Fix Required:**
- Use Supabase upsert operations
- Handle unique constraint violations
- Add retry logic with exponential backoff

---

### 5. ❌ **Secrets Import Inside Function**
**Location:** `apps/api/app/api/routes/plex_auth.py:88`  
**Severity:** MEDIUM  
**Status:** 🔴 **NEEDS FIX**

```python
import secrets  # Inside the function!
temp_password = secrets.token_urlsafe(32)
```

**Issue:**
- Imports should be at module level
- Performance penalty on every auth request
- Makes testing harder
- Violates PEP 8

**Fix:** Move to top of file with other imports

---

### 6. ❌ **No Password Hashing for Temp Passwords**
**Location:** `apps/api/app/api/routes/plex_auth.py:89`  
**Severity:** HIGH  
**Status:** 🔴 **SECURITY RISK**

```python
temp_password = secrets.token_urlsafe(32)

auth_response = supabase.auth.admin.create_user({
    "email": email,
    "password": temp_password,  # Plain text!
    "email_confirm": True,
})
```

**Issue:**
- While these are temporary, they're sent to Supabase
- If Supabase stores them (even temporarily), they're exposed
- No secure cleanup after use

**Impact:** Potential password exposure in logs/memory

**Fix:** Use Supabase's password-less user creation if available, or ensure hashing

---

## High Severity Issues 🟠

### 7. ❌ **No Request Timeout Configuration**
**Location:** `apps/api/app/api/routes/plex_auth.py:212-217`  
**Severity:** HIGH  

**Issue:**
```python
user_response = await client.get(
    'https://plex.tv/users/account.json',
    headers=headers,
    timeout=10.0  # GOOD!
)
```

**But in login-form.tsx:**
```typescript
const loginResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/plex/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ authToken: checkData.authToken }),
    // NO TIMEOUT! Could hang forever
})
```

**Impact:** Frontend hangs indefinitely if backend is slow

**Fix:** Add timeout to all fetch calls

---

### 8. ❌ **Frontend Polls Forever on Error**
**Location:** `apps/web/src/components/auth/login-form.tsx:66-86`  
**Severity:** HIGH  

**Issue:**
```typescript
const pollInterval = setInterval(async () => {
    const checkResponse = await fetch(`https://plex.tv/api/v2/pins/${pinData.id}`, ...)
    
    if (checkData.authToken) {
        clearInterval(pollInterval)  // Only cleared on success!
    }
}, 2000)
```

**Problems:**
- No error handling in polling loop
- If Plex API errors, keeps polling forever (until 5min timeout)
- Network errors aren't caught
- Interval ID might leak if component unmounts

**Impact:** 
- Wasted API calls
- Battery drain on mobile
- Memory leaks

**Fix:**
```typescript
let pollInterval: NodeJS.Timeout | null = null
let pollCount = 0
const MAX_POLLS = 150 // 5 minutes at 2sec intervals

try {
    pollInterval = setInterval(async () => {
        pollCount++
        
        if (pollCount > MAX_POLLS) {
            if (pollInterval) clearInterval(pollInterval)
            setError('Polling timeout')
            return
        }
        
        try {
            const checkResponse = await fetch(...)
            if (!checkResponse.ok) {
                console.warn('Poll failed:', checkResponse.status)
                return // Continue polling
            }
            // ... rest of logic
        } catch (err) {
            console.error('Poll error:', err)
            // Continue polling - might be transient
        }
    }, 2000)
} catch (err) {
    if (pollInterval) clearInterval(pollInterval)
    throw err
}

// Add cleanup on unmount
useEffect(() => {
    return () => {
        if (pollInterval) clearInterval(pollInterval)
    }
}, [])
```

---

### 9. ❌ **No Validation of Plex Token Response**
**Location:** `apps/api/app/api/routes/plex_auth.py:197-225`  
**Severity:** HIGH  

**Issue:**
```python
user_data = user_response.json()
user_account = user_data.get('user', {})

return {
    'id': user_account.get('id'),  # Could be None!
    'username': user_account.get('username'),  # Could be None!
    'email': user_account.get('email'),  # Could be None!
}
```

**Problems:**
- No validation that required fields exist
- `id` and `username` could be `None`, causing downstream errors
- No schema validation of Plex response

**Impact:** Crashes when Plex API changes or returns unexpected data

**Fix:**
```python
user_account = user_data.get('user', {})

if not user_account.get('id') or not user_account.get('username'):
    raise ValueError("Invalid Plex response: missing required user fields")

return {
    'id': user_account['id'],  # Now guaranteed to exist
    'username': user_account['username'],
    'email': user_account.get('email'),  # Email is optional
    'title': user_account.get('title') or user_account['username'],
    'thumb': user_account.get('thumb'),
    'authToken': auth_token
}
```

---

### 10. ❌ **LocalStorage Used for Sensitive Data**
**Location:** `apps/web/src/components/auth/login-form.tsx:92-96, 130-134`  
**Severity:** HIGH - **SECURITY RISK**  

**Issue:**
```typescript
localStorage.setItem('smartplex_user', JSON.stringify(user))
localStorage.setItem('smartplex_session', JSON.stringify(supabase_session))
localStorage.setItem('plex_token', checkData.authToken)  // SENSITIVE!
```

**Problems:**
- localStorage is accessible to all JavaScript on the domain
- Not encrypted
- Persists across sessions (XSS risk)
- Plex token gives full account access!

**Impact:** 
- XSS attacks can steal tokens
- Token theft = account compromise
- No expiration enforcement

**Fix:**
- Use httpOnly cookies for tokens (backend sets them)
- Store only non-sensitive data in localStorage
- Use Supabase's built-in session management

---

### 11. ❌ **No CSRF Protection**
**Location:** All API endpoints  
**Severity:** HIGH - **SECURITY RISK**  

**Issue:**
- No CSRF tokens
- No SameSite cookie attributes
- Stateless auth makes CSRF possible

**Impact:** Cross-site request forgery attacks possible

**Fix:** Implement CSRF tokens or use SameSite=Strict cookies

---

### 12. ❌ **Database Schema Allows NULL on Critical Fields**
**Location:** `packages/db/schema.sql`  
**Severity:** MEDIUM  

**Issues:**
```sql
CREATE TABLE users (
  display_name TEXT,  -- Should have default
  avatar_url TEXT,    -- OK to be null
  last_active_at TIMESTAMP WITH TIME ZONE,  -- Should default to NOW()
)

CREATE TABLE media_items (
  year INTEGER,  -- OK to be null for ongoing series
  imdb_id TEXT,  -- OK to be null
  file_path TEXT,  -- Should NOT be null!
  file_size_bytes BIGINT,  -- Should NOT be null!
)
```

**Fix:**
```sql
display_name TEXT NOT NULL DEFAULT 'User',
last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
file_path TEXT NOT NULL,
file_size_bytes BIGINT NOT NULL DEFAULT 0,
```

---

## Medium Severity Issues 🟡

### 13. ❌ **Random Import Inside Function**
**Location:** `apps/api/app/api/routes/ai.py:90`  

```python
def chat_with_ai(...):
    # ... code ...
    import random  # Should be at top!
    response_text = random.choice(mock_responses)
```

**Fix:** Move import to module level

---

### 14. ❌ **No Rate Limiting**
**Location:** All API endpoints  
**Severity:** MEDIUM  

**Issue:**
- No rate limiting on auth endpoints
- Could be DDoS'd easily
- No IP-based throttling
- Plex API polling could hit rate limits

**Fix:** Implement rate limiting middleware (e.g., slowapi)

---

### 15. ❌ **Mock Data in Production Endpoints**
**Location:** `sync.py`, `ai.py`  
**Severity:** MEDIUM  

**Issue:**
```python
# Mock sync data for demo
mock_media_items = [...]

# In production: supabase.table("sync_history").insert(sync_record).execute()
```

**Problems:**
- Returns fake data in production
- Commented code that should be implemented
- Users won't see real data

**Fix:** Implement actual Plex API integration or throw NotImplementedError

---

### 16. ❌ **No Logging Strategy**
**Location:** Everywhere  
**Severity:** MEDIUM  

**Issue:**
- Using `print()` statements everywhere
- No structured logging
- No log levels (debug, info, error)
- No log aggregation

**Fix:** Implement proper logging with Python's `logging` module

---

### 17. ❌ **Error Messages Expose Internal Details**
**Location:** Multiple exception handlers  
**Severity:** MEDIUM - **SECURITY RISK**  

**Issue:**
```python
raise HTTPException(
    status_code=401,
    detail=f"Plex authentication failed: {str(e)}"  # Exposes stack trace!
)
```

**Fix:**
```python
print(f"❌ Internal error: {str(e)}")  # Log it
raise HTTPException(
    status_code=401,
    detail="Authentication failed"  # Generic message to user
)
```

---

### 18. ❌ **No Input Validation on Query Parameters**
**Location:** `ai.py:237`, `sync.py:119`  

**Issue:**
```python
@router.get("/history")
async def get_sync_history(
    limit: int = 10,  # No max limit!
)
```

**Problems:**
- Could request 1 million records
- No pagination
- No max limit enforcement

**Fix:**
```python
limit: int = Field(default=10, ge=1, le=100)  # Max 100
```

---

### 19. ❌ **Missing Environment Variable Defaults**
**Location:** `apps/api/app/config.py`  

**Issue:**
```python
supabase_url: str = Field(..., alias="SUPABASE_URL")  # No default = crash if missing
```

**Problem:** App crashes on startup if env var missing (good for required vars, but error message is cryptic)

**Improvement:** Add validation error message or use default for non-critical vars

---

### 20. ❌ **No Health Check for Dependencies**
**Location:** `apps/api/app/api/routes/health.py:50`  

**Issue:**
```python
response = supabase.table("users").select("id").limit(1).execute()
```

**Problems:**
- Queries actual table (slow)
- Could return empty result but database is fine
- No check for Redis, AI services, etc.

**Fix:** Use connection-only health checks, not data queries

---

## Low Severity Issues (Technical Debt) 🟢

### 21. ⚠️ **Inconsistent Naming Conventions**
- `get_settings()` vs `get_supabase_client()` (both should use same caching pattern)
- `smartplex_user` vs `smartplex_session` (inconsistent prefixes in localStorage)

---

### 22. ⚠️ **No TypeScript for Frontend API Responses**
- API responses aren't typed
- No shared types between backend/frontend
- Could use OpenAPI codegen

---

### 23. ⚠️ **No Database Migrations Strategy**
- Running raw SQL files manually
- No versioning
- No rollback strategy
- Should use Supabase migrations or Alembic

---

## Dependency Issues 📦

### 24. ❌ **Python Version Mismatch**
**Location:** `pyproject.toml`  

**Issue:**
```toml
python = "^3.11"  # Says 3.11+
```

But Railway uses Python 3.13 in production (nixpacks.toml)!

**Impact:** Could have subtle incompatibilities

**Fix:** Lock to specific version or test on 3.13

---

### 25. ❌ **Missing Dependencies**
- No `pytest-cov` for coverage
- No `httpx` in main dependencies (used in plex_auth but only in dev)
- No `redis` client usage (imported but not used)

---

## Summary Statistics

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| 🔴 Critical | 6 | 1 | 5 |
| 🟠 High | 6 | 0 | 6 |
| 🟡 Medium | 9 | 0 | 9 |
| 🟢 Low | 4 | 0 | 4 |
| **Total** | **25** | **1** | **24** |

---

## Immediate Action Items (Priority Order)

### 🚨 **MUST FIX BEFORE NEXT DEPLOYMENT:**

1. **Remove `@lru_cache()` from `get_supabase_client()`** ← Same bug that just crashed prod
2. **Add error handling to all Supabase `.execute()` calls**
3. **Add timeout to frontend fetch calls**
4. **Fix polling cleanup and error handling in login-form**
5. **Move localStorage tokens to httpOnly cookies**

### 📋 **Should Fix This Week:**

6. Implement proper logging (replace print statements)
7. Add request validation (max limits, field validation)
8. Add CSRF protection
9. Fix race condition in user creation
10. Validate Plex API responses

### 📝 **Technical Debt to Address:**

11. Replace mock endpoints with real implementations
12. Add rate limiting
13. Implement database migrations
14. Add TypeScript types for API
15. Set up proper error monitoring (Sentry)

---

## Testing Recommendations

**Currently:** No tests exist!

**Add:**
1. Unit tests for all route handlers
2. Integration tests for auth flow
3. E2E tests for critical paths
4. Load testing for rate limits
5. Security testing (OWASP Top 10)

---

## Conclusion

The codebase has a **solid foundation** but contains several **production-breaking bugs** and **security vulnerabilities** that need immediate attention.

**Key Takeaways:**
- The `lru_cache` issue is a pattern that appears twice
- Error handling is insufficient throughout
- Security practices need improvement
- Many "TODO" items are in production code

**Estimated Fix Time:**
- Critical issues: 4-6 hours
- High severity: 8-10 hours
- Medium severity: 12-16 hours
- Total: **2-3 days of focused work**

