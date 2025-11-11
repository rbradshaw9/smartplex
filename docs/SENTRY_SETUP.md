# Sentry Error Tracking Setup

SmartPlex uses Sentry for error tracking and performance monitoring in both frontend and backend.

## Sentry Projects

We use **2 separate Sentry projects** for better organization:

1. **smartplex-web** (Next.js Frontend)
   - Organization: `tactiqal`
   - Project: `smartplex-web`
   - DSN: `https://0384e7109635342e54c2f9916a6a8daf@o4510303274926080.ingest.us.sentry.io/4510346716643328`

2. **smartplex-api** (Python/FastAPI Backend)
   - Organization: `tactiqal`
   - Project: `smartplex-api`
   - DSN: `https://9352877a711f16edf148d59fd3d7900b@o4510303274926080.ingest.us.sentry.io/4510346730733568`

## Setup Instructions

### 1. Frontend (Next.js) - Already Configured ✅

The frontend Sentry SDK is already installed and configured with the DSN.

**Configuration files:**
- `apps/web/sentry.client.config.ts` - Client-side tracking
- `apps/web/sentry.server.config.ts` - Server-side tracking
- `apps/web/sentry.edge.config.ts` - Edge runtime tracking

**Environment Variables (Optional Override):**
```bash
# apps/web/.env.local
NEXT_PUBLIC_SENTRY_DSN=https://0384e7109635342e54c2f9916a6a8daf@o4510303274926080.ingest.us.sentry.io/4510346716643328
SENTRY_ORG=tactiqal
SENTRY_PROJECT=smartplex-web
```

### 2. Backend (FastAPI) - Already Configured ✅

The backend Sentry SDK is already installed and configured with the DSN.

**Configuration location:**
- `apps/api/app/main.py` - Sentry initialization with FastAPI integration

**Environment Variables (Optional Override):**
```bash
# apps/api/.env
SENTRY_DSN=https://9352877a711f16edf148d59fd3d7900b@o4510303274926080.ingest.us.sentry.io/4510346730733568
```

### 3. Deploy to Railway

The DSNs are **hardcoded in the code** as fallback values, so Sentry works out of the box.

**Optional:** To override the DSN in Railway:
1. Go to Railway dashboard
2. Select your project
3. Click on "Variables" tab
4. Add `SENTRY_DSN` for the API service
5. Add `NEXT_PUBLIC_SENTRY_DSN` for the web service

## Features

### Frontend (Next.js)
- Automatic error capture for client, server, and edge runtimes
- Session replay for debugging user issues
- Performance monitoring
- Breadcrumb tracking
- Sensitive data filtering (passwords, tokens)

### Backend (FastAPI)
- Automatic exception capture
- Request/response tracking
- Performance tracing
- Integration with FastAPI and Starlette

## Testing

### Frontend Testing
Open browser console on any authenticated page and run:
```javascript
throw new Error("Test Sentry Error from Frontend");
```

Check errors at: https://tactiqal.sentry.io/issues/?project=4510346716643328

### Backend Testing
Visit the debug endpoint:
```bash
# Local
curl http://localhost:8000/sentry-debug

# Production
curl https://smartplexapi-production.up.railway.app/sentry-debug
```

Check errors at: https://tactiqal.sentry.io/issues/?project=4510346730733568

## Privacy & Security

- All sensitive data (passwords, API keys, tokens) are filtered before sending to Sentry
- Session replays mask all text and media by default
- If `SENTRY_DSN` is not configured, no data is sent
- Adjust `tracesSampleRate` in production to reduce volume (e.g., 0.1 for 10% sampling)

## Beta Testers

For beta testing, Sentry helps track:
- Frontend errors (React, Next.js)
- API errors (500s, 400s)
- Performance issues
- User session replays for bug reproduction
- Real-time error alerts

## Monitoring

View errors in real-time at:
- **Frontend**: https://tactiqal.sentry.io/issues/?project=4510346716643328
- **Backend**: https://tactiqal.sentry.io/issues/?project=4510346730733568
- **All Projects**: https://tactiqal.sentry.io/issues/

## Cost

Sentry free tier includes:
- 5,000 errors/month
- 100 session replays/month
- 10,000 performance units/month

This is sufficient for beta testing with <100 users.
