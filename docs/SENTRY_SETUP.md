# Sentry Error Tracking Setup

SmartPlex uses Sentry for error tracking and performance monitoring in both frontend and backend.

## Setup Instructions

### 1. Create Sentry Account
1. Go to [sentry.io](https://sentry.io) and create a free account
2. Create a new project for "Next.js" (for frontend) and "Python" (for backend)
3. Copy your DSN (Data Source Name) from the project settings

### 2. Configure Environment Variables

#### Frontend (apps/web/.env.local)
```bash
NEXT_PUBLIC_SENTRY_DSN=https://your-frontend-dsn@sentry.io/project-id
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=smartplex-web
```

#### Backend (apps/api/.env)
```bash
SENTRY_DSN=https://your-backend-dsn@sentry.io/project-id
```

### 3. Deploy to Railway

Add the environment variables to your Railway project:

1. Go to Railway dashboard
2. Select your project
3. Click on "Variables" tab
4. Add `SENTRY_DSN` for the API service
5. Add `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_ORG`, and `SENTRY_PROJECT` for the web service

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

To test Sentry is working:

### Frontend
Open browser console and run:
```javascript
throw new Error("Test Sentry Error from Frontend");
```

### Backend
Visit: `https://your-api-url/sentry-debug`

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
- Frontend: https://sentry.io/organizations/your-org/issues/?project=smartplex-web
- Backend: https://sentry.io/organizations/your-org/issues/?project=smartplex-api

## Cost

Sentry free tier includes:
- 5,000 errors/month
- 100 session replays/month
- 10,000 performance units/month

This is sufficient for beta testing with <100 users.
